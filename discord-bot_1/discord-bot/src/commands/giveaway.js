// src/commands/giveaway.js
const { SlashCommandBuilder, PermissionFlagsBits, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');

const activeGiveaways = new Map();

module.exports = {
  data: new SlashCommandBuilder()
    .setName('giveaway')
    .setDescription('🎁 Start a giveaway')
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages)
    .addStringOption(o => o.setName('prize').setDescription('What are you giving away?').setRequired(true))
    .addIntegerOption(o => o.setName('minutes').setDescription('How many minutes should it last?').setRequired(true).setMinValue(1).setMaxValue(10080))
    .addIntegerOption(o => o.setName('winners').setDescription('How many winners?').setRequired(false).setMinValue(1).setMaxValue(20)),

  async execute(interaction) {
    const prize    = interaction.options.getString('prize');
    const minutes  = interaction.options.getInteger('minutes');
    const winners  = interaction.options.getInteger('winners') || 1;
    const endsAt   = new Date(Date.now() + minutes * 60 * 1000);
    const endsTs   = Math.floor(endsAt.getTime() / 1000);

    const embed = new EmbedBuilder()
      .setColor(0xFBBF24)
      .setTitle('🎁 GIVEAWAY!')
      .setDescription([
        `## ${prize}`,
        ``,
        `**Click the button below to enter!**`,
        ``,
        `🏆 **Winners:** ${winners}`,
        `⏰ **Ends:** <t:${endsTs}:R> (<t:${endsTs}:f>)`,
        `👤 **Hosted by:** ${interaction.user}`,
      ].join('\n'))
      .setThumbnail('https://media.discordapp.net/attachments/1078231423286566932/gift.gif')
      .setTimestamp(endsAt)
      .setFooter({ text: `Ends at`, iconURL: interaction.guild.iconURL({ dynamic: true }) });

    const row = new ActionRowBuilder().addComponents(
      new ButtonBuilder()
        .setCustomId('giveaway_enter')
        .setLabel('0 Entries')
        .setEmoji('🎉')
        .setStyle(ButtonStyle.Primary)
    );

    await interaction.reply({ content: '✅ Giveaway started!', ephemeral: true });
    const msg = await interaction.channel.send({ content: '> 🎁 **NEW GIVEAWAY** — React below to enter!', embeds: [embed], components: [row] });

    const entrants = new Set();
    activeGiveaways.set(msg.id, { entrants, winners, prize, msg });

    // Handle entries via collector
    const collector = msg.createMessageComponentCollector({ time: minutes * 60 * 1000 });

    collector.on('collect', async btn => {
      if (btn.customId !== 'giveaway_enter') return;
      const uid = btn.user.id;
      if (entrants.has(uid)) {
        entrants.delete(uid);
        await btn.reply({ content: '❌ You left the giveaway.', ephemeral: true });
      } else {
        entrants.add(uid);
        await btn.reply({ content: '🎉 You entered the giveaway! Good luck!', ephemeral: true });
      }
      // Update button label
      const updatedRow = new ActionRowBuilder().addComponents(
        new ButtonBuilder()
          .setCustomId('giveaway_enter')
          .setLabel(`${entrants.size} Entries`)
          .setEmoji('🎉')
          .setStyle(ButtonStyle.Primary)
      );
      await btn.message.edit({ components: [updatedRow] }).catch(() => {});
    });

    collector.on('end', async () => {
      const entrantArr = [...entrants];
      const winnerIds  = [];
      const pool       = [...entrantArr];
      for (let i = 0; i < Math.min(winners, pool.length); i++) {
        const idx = Math.floor(Math.random() * pool.length);
        winnerIds.push(pool.splice(idx, 1)[0]);
      }

      const winnerMentions = winnerIds.map(id => `<@${id}>`).join(', ') || 'No valid entrants 😢';

      const endEmbed = new EmbedBuilder()
        .setColor(0x22C55E)
        .setTitle('🎁 Giveaway Ended!')
        .setDescription([
          `## ${prize}`,
          ``,
          `🏆 **Winner(s):** ${winnerMentions}`,
          `👥 **Total Entries:** ${entrantArr.length}`,
          `👤 **Hosted by:** ${interaction.user}`,
        ].join('\n'))
        .setTimestamp()
        .setFooter({ text: 'Giveaway ended', iconURL: interaction.guild.iconURL({ dynamic: true }) });

      const disabledRow = new ActionRowBuilder().addComponents(
        new ButtonBuilder()
          .setCustomId('giveaway_ended')
          .setLabel(`${entrantArr.length} Entries — Ended`)
          .setEmoji('🎉')
          .setStyle(ButtonStyle.Secondary)
          .setDisabled(true)
      );

      await msg.edit({ embeds: [endEmbed], components: [disabledRow] }).catch(() => {});
      if (winnerIds.length > 0) {
        await interaction.channel.send({
          content: `🎉 Congratulations ${winnerMentions}! You won **${prize}**!`,
        });
      }
      activeGiveaways.delete(msg.id);
    });
  }
};
