// src/commands/perks.js
const { SlashCommandBuilder, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');

const DISCORD_INVITE = 'https://discord.gg/CZ28Gh3wXG';
const ROBLOX_GROUP   = 'https://www.roblox.com/share/g/35116281';

module.exports = {
  data: new SlashCommandBuilder()
    .setName('perks')
    .setDescription('💎 View supporter & booster perks'),

  async execute(interaction) {
    const member = interaction.member;
    const guild  = interaction.guild;

    const isSupporter = member.roles.cache.some(r => r.name.toLowerCase().includes('supporter'));
    const isBooster   = member.premiumSince != null;

    const embed = new EmbedBuilder()
      .setTimestamp()
      .setFooter({ text: guild.name, iconURL: guild.iconURL({ dynamic: true }) });

    if (isBooster) {
      embed
        .setColor(0xF472B6)
        .setTitle('🚀 Booster Perks — Thank You for Boosting!')
        .setThumbnail(member.user.displayAvatarURL({ dynamic: true, size: 256 }))
        .setDescription([
          `## Hey ${member}, you're a Server Booster! 💖`,
          '',
          'You get **everything Supporters get**, plus:',
          '',
          '🚀 **Exclusive Booster role** with a pink colour',
          '💎 **Supporter access** — VIP chat, VIP voice, perks channel',
          '👑 **Priority support** from staff',
          '🎨 **Custom colour role** — ask a staff member',
          '📣 **Shoutout in #boosts** every time you boost',
          '⭐ **Your name highlighted** in the member list',
          '',
          '> You are the backbone of this server. We love you. 💜',
        ].join('\n'));
    } else if (isSupporter) {
      embed
        .setColor(0xA855F7)
        .setTitle('💎 Supporter Perks')
        .setThumbnail(member.user.displayAvatarURL({ dynamic: true, size: 256 }))
        .setDescription([
          `## Hey ${member}, you're a Supporter! ✨`,
          '',
          '💎 **Access to the Supporters section** — exclusive channels',
          '👑 **VIP Chat** — private chat with other supporters & staff',
          '🔊 **VIP Voice** — exclusive voice channel',
          '🌟 **Supporters role** — highlighted in the member list',
          '📢 **Early access** to announcements and updates',
          '💜 **Priority support** from staff',
          '',
          '> Boost the server to unlock even more perks!',
        ].join('\n'));
    } else {
      embed
        .setColor(0x6366F1)
        .setTitle('✨ Supporter & Booster Perks')
        .setDescription([
          '**Want exclusive perks? Here\'s how to get them:**',
          '',
          '## 💎 Supporter',
          '> Ask a staff member to give you the Supporter role.',
          '• Access to VIP chat & voice',
          '• Exclusive supporters section',
          '• Highlighted in member list',
          '• Priority staff support',
          '',
          '## 🚀 Booster',
          '> Boost the server to unlock all Supporter perks PLUS:',
          '• Pink Booster role colour',
          '• Custom colour role on request',
          '• Shoutout in #boosts',
          '• Name at the top of the member list',
          '',
          `💬 **Discord:** [Join here](${DISCORD_INVITE})`,
          `🎮 **Roblox Group:** [Join here](${ROBLOX_GROUP})`,
        ].join('\n'));
    }

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
