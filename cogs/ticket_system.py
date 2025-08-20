import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, File, PermissionOverwrite
from nextcord.ui import View, Select, Button, button
import config
from pymongo import MongoClient
import datetime
import asyncio
from io import BytesIO

try:
    mongo_client = MongoClient(config.MONGO_URI)
    db = mongo_client["TicketBotDB"]
    tickets_collection = db["tickets"]
    print("Cog: Successfully connected to MongoDB.")
except Exception as e:
    print(f"Cog: Error connecting to MongoDB: {e}")
    tickets_collection = None


class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Close Ticket", style=nextcord.ButtonStyle.red, custom_id="close_ticket_button")
    async def close_button_callback(self, button: Button, interaction: Interaction):
        ticket_data = tickets_collection.find_one({"channel_id": interaction.channel.id, "status": "open"})
        
        if ticket_data:
            await interaction.response.send_message("This ticket is being closed and transcribed. It will be deleted in 5 seconds.")
            
            log_channel = interaction.guild.get_channel(config.LOG_CHANNEL_ID)
            
            if log_channel:
                messages = [msg async for msg in interaction.channel.history(limit=None, oldest_first=True)]
                
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Ticket Transcript: {interaction.channel.name}</title>
                    <style>
                        body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #36393f; color: #dcddde; margin: 0; padding: 20px; }}
                        .container {{ max-width: 800px; margin: auto; background-color: #2f3136; border-radius: 8px; padding: 20px; }}
                        .header {{ text-align: center; border-bottom: 1px solid #40444b; padding-bottom: 10px; margin-bottom: 20px; }}
                        .header h1 {{ color: #ffffff; }}
                        .message {{ display: flex; margin-bottom: 15px; }}
                        .message .avatar {{ width: 40px; height: 40px; border-radius: 50%; margin-right: 15px; }}
                        .message .content {{ flex-grow: 1; }}
                        .message .author {{ font-weight: bold; color: #ffffff; }}
                        .message .timestamp {{ font-size: 0.75em; color: #72767d; margin-left: 5px; }}
                        .message .text {{ margin-top: 5px; white-space: pre-wrap; word-wrap: break-word; }}
                        .attachment img {{ max-width: 400px; border-radius: 5px; margin-top: 10px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>Ticket Transcript</h1>
                            <p>Channel: <strong>{interaction.channel.name}</strong></p>
                        </div>
                """
                
                for msg in messages:
                    author_name = msg.author.display_name
                    avatar_url = msg.author.display_avatar.url
                    timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
                    
                    html_content += f"""
                        <div class="message">
                            <img src="{avatar_url}" alt="{author_name}'s Avatar" class="avatar">
                            <div class="content">
                                <div>
                                    <span class="author">{author_name}</span>
                                    <span class="timestamp">{timestamp}</span>
                                </div>
                                <div class="text">{msg.content}</div>
                    """
                    if msg.attachments:
                        for attachment in msg.attachments:
                            if attachment.content_type.startswith('image/'):
                                html_content += f'<div class="attachment"><a href="{attachment.url}" target="_blank"><img src="{attachment.url}" alt="Attachment"></a></div>'
                            else:
                                html_content += f'<div class="attachment"><a href="{attachment.url}" target="_blank">Download: {attachment.filename}</a></div>'

                    html_content += "</div></div>"

                html_content += "</div></body></html>"
                
                transcript_file = File(
                    BytesIO(html_content.encode('utf-8')),
                    filename=f"transcript-{interaction.channel.name}.html"
                )
                
                log_embed = nextcord.Embed(
                    title="Ticket Closed & Transcript Saved",
                    description=f"Ticket **{interaction.channel.name}** was closed by {interaction.user.mention}.",
                    color=nextcord.Color.orange(),
                    timestamp=datetime.datetime.utcnow()
                )
                opener = interaction.guild.get_member(ticket_data['opener_id'])
                if opener:
                    log_embed.add_field(name="Opened By", value=opener.mention)

                await log_channel.send(embed=log_embed, file=transcript_file)
            
            await asyncio.sleep(5)
            
            tickets_collection.update_one(
                {"channel_id": interaction.channel.id},
                {"$set": {"status": "closed", "closed_at": datetime.datetime.utcnow(), "closed_by": interaction.user.id}}
            )
            
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
        else:
            await interaction.response.send_message("This ticket is already being closed or could not be found.", ephemeral=True)


class TicketSelect(Select):
    def __init__(self):
        options = [
            nextcord.SelectOption(label="Technical Support", description="For technical issues.", emoji="🔧", value="support"),
            nextcord.SelectOption(label="Report a User", description="Report rule violations.", emoji="🛡️", value="report"),
            nextcord.SelectOption(label="General Question", description="For other inquiries.", emoji="❓", value="question"),
        ]
        super().__init__(placeholder="Choose a ticket category...", options=options, custom_id="ticket_select_menu")

    async def callback(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True, with_message=True)
        if tickets_collection is not None and tickets_collection.find_one({"opener_id": interaction.user.id, "status": "open"}):
            await interaction.followup.send("You already have an open ticket.", ephemeral=True)
            return
        guild = interaction.guild
        category = nextcord.utils.get(guild.categories, name="Tickets")
        staff_role = nextcord.utils.get(guild.roles, name="Staff")
        if not category:
            await interaction.followup.send("Error: 'Tickets' category not found. Please create it.", ephemeral=True)
            return
        overwrites = {guild.default_role: PermissionOverwrite(read_messages=False), interaction.user: PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True), guild.me: PermissionOverwrite(read_messages=True, send_messages=True)}
        if staff_role:
            overwrites[staff_role] = PermissionOverwrite(read_messages=True, send_messages=True)
        ticket_type = self.values[0]
        channel_name = f"{ticket_type}-{interaction.user.name}"
        try:
            channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        except nextcord.Forbidden:
            await interaction.followup.send("I don't have permissions to create channels.", ephemeral=True)
            return
        ticket_data = {"channel_id": channel.id, "opener_id": interaction.user.id, "status": "open", "type": ticket_type, "opened_at": datetime.datetime.utcnow(), "closed_at": None, "closed_by": None}
        if tickets_collection is not None:
            tickets_collection.insert_one(ticket_data)
        welcome_embed = nextcord.Embed(title=f"{ticket_type.capitalize()} Ticket", description=f"Welcome, {interaction.user.mention}! A staff member will be with you shortly.\nPlease describe your issue in detail.", color=nextcord.Color.green())
        await channel.send(content=staff_role.mention if staff_role else "", embed=welcome_embed, view=CloseTicketView())
        await interaction.followup.send(f"Your ticket has been created at {channel.mention}!", ephemeral=True)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(TicketView())
        self.bot.add_view(CloseTicketView())
        print("Persistent views for tickets have been added.")
    @nextcord.slash_command(name="setup-tickets", description="Sets up the ticket creation panel in a channel.", guild_ids=[config.SERVER_ID])
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, interaction: Interaction, channel: nextcord.TextChannel = SlashOption(name="channel", description="The channel to send the ticket panel to.", required=True)):
        await interaction.response.defer(ephemeral=True)
        embed = nextcord.Embed(title="Support Center", description="To open a ticket, please select a category from the dropdown menu below.", color=nextcord.Color.blue())
        await channel.send(embed=embed, view=TicketView())
        await interaction.followup.send(f"The ticket panel has been set up in {channel.mention}!", ephemeral=True)

def setup(bot):
    bot.add_cog(TicketSystem(bot))