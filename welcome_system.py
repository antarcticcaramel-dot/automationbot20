import discord
from discord.ui import View, Button

class WelcomeOnboardView(View):
    def __init__(self, rules_ch_id: int, verify_ch_id: int):
        super().__init__(timeout=None)
        
        # V2 Link Buttons
        rules_btn = Button(label="📖 Read Rules", style=discord.ButtonStyle.link, url=f"https://discord.com/channels/@me/{rules_ch_id}")
        verify_btn = Button(label="✅ Get Verified", style=discord.ButtonStyle.link, url=f"https://discord.com/channels/@me/{verify_ch_id}")
        
        self.add_item(rules_btn)
        self.add_item(verify_btn)

    @discord.ui.button(label="👋 Say Hi", style=discord.ButtonStyle.primary, custom_id="say_hi_btn")
    async def say_hi(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(f"{interaction.user.mention} just said hi to everyone! 👋")
        button.disabled = True
        await interaction.message.edit(view=self)

async def send_advanced_welcome(member: discord.Member, channel: discord.TextChannel, rules_id: int, verify_id: int):
    """Sends an advanced V2 component welcome message."""
    embed = discord.Embed(
        title=f"Welcome to {member.guild.name}! 🎉",
        description=f"Hey {member.mention}, we are thrilled to have you here! You are our **{member.guild.member_count}th** member.\n\n"
                    f"**Next Steps:**\n"
                    f"1️⃣ Read the rules\n"
                    f"2️⃣ Get verified to access all channels\n"
                    f"3️⃣ Introduce yourself!",
        color=0x5865F2
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    if member.guild.banner:
        embed.set_image(url=member.guild.banner.url)
    
    view = WelcomeOnboardView(rules_id, verify_id)
    await channel.send(content=member.mention, embed=embed, view=view)

def setup(bot):
    @bot.event
    async def on_member_join(member):
        # Fallback search for welcome channel
        welcome_ch = discord.utils.find(lambda c: "welcome" in c.name.lower(), member.guild.text_channels)
        rules_ch = discord.utils.find(lambda c: "rule" in c.name.lower(), member.guild.text_channels)
        verify_ch = discord.utils.find(lambda c: "verify" in c.name.lower() or "get-started" in c.name.lower(), member.guild.text_channels)
        
        if welcome_ch:
            r_id = rules_ch.id if rules_ch else welcome_ch.id
            v_id = verify_ch.id if verify_ch else welcome_ch.id
            await send_advanced_welcome(member, welcome_ch, r_id, v_id)
