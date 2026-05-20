// src/commands/testboost.js
const { SlashCommandBuilder, PermissionFlagsBits, EmbedBuilder } = require('discord.js');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('testboost')
    .setDescription('🚀 Simulate a server boost announcement (admin only)')
    .setDefaultMemberPermissions(PermissionFlagsBits.Administrator),

  async execute(interaction) {
    const guild  = interaction.guild;
    const member = interaction.member;

    const boostChannel =
      guild.channels.cache.find(c => c.name.includes('boost') && c.isTextBased()) ||
      guild.channels.cache.find(c => c.name.includes('general') && c.isTextBased());

    if (!boostChannel) {
      await interaction.reply({ content: '❌ No boosts or general channel found.', ephemeral: true });
      return;
    }

    const embed = new EmbedBuilder()
      .setColor(0xF472B6)
      .setTitle('🚀 Server Boosted!')
      .setDescription([
        `## ${member} just boosted the server! 💎`,
        ``,
        `Thank you so much for your support! ❤️`,
        `You're helping us unlock amazing perks for everyone.`,
        ``,
        `**Current Boost Level:** ${guild.premiumTier === 0 ? 'No Level' : `Level ${guild.premiumTier}`}`,
        `**Total Boosts:** ${guild.premiumSubscriptionCount} 🚀`,
        ``,
        `*⚠️ This is a test boost — no real boost was made.*`,
      ].join('\n'))
      .setThumbnail(member.user.displayAvatarURL({ dynamic: true, size: 256 }))
      .setImage('https://media.discordapp.net/attachments/858992969651961876/1073249983542800395/boost.gif')
      .setTimestamp()
      .setFooter({ text: `${guild.name} • TEST BOOST`, iconURL: guild.iconURL({ dynamic: true }) });

    await boostChannel.send({
      content: `> 🌟 **[TEST]** ${member} just became a Server Booster!`,
      embeds: [embed]
    });

    await interaction.reply({
      embeds: [new EmbedBuilder()
        .setColor(0x22C55E)
        .setDescription(`✅ Test boost posted in ${boostChannel}!`)
      ],
      ephemeral: true
    });
  }
};
