// src/commands/links.js
const { SlashCommandBuilder, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');

const DISCORD_INVITE = 'https://discord.gg/CZ28Gh3wXG';
const ROBLOX_GROUP   = 'https://www.roblox.com/share/g/35116281';

module.exports = {
  data: new SlashCommandBuilder()
    .setName('links')
    .setDescription('🔗 Get all important server links'),

  async execute(interaction) {
    const guild = interaction.guild;

    const embed = new EmbedBuilder()
      .setColor(0xA855F7)
      .setTitle('🔗 Important Links')
      .setDescription([
        '**Everything you need in one place!**',
        '',
        `💬 **Discord Server** — [Join for support & community](${DISCORD_INVITE})`,
        `🎮 **Roblox Group** — [Join our Roblox group](${ROBLOX_GROUP})`,
        '',
        '> Need help? Join the Discord and a staff member will assist you! 💜',
      ].join('\n'))
      .setThumbnail(guild.iconURL({ dynamic: true, size: 256 }))
      .setTimestamp()
      .setFooter({ text: guild.name, iconURL: guild.iconURL({ dynamic: true }) });

    const row = new ActionRowBuilder().addComponents(
      new ButtonBuilder()
        .setLabel('Join Discord')
        .setEmoji('💬')
        .setStyle(ButtonStyle.Link)
        .setURL(DISCORD_INVITE),
      new ButtonBuilder()
        .setLabel('Join Roblox Group')
        .setEmoji('🎮')
        .setStyle(ButtonStyle.Link)
        .setURL(ROBLOX_GROUP),
    );

    await interaction.reply({ embeds: [embed], components: [row] });
  }
};
