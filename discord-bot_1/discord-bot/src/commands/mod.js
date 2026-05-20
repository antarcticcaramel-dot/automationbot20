// src/commands/mod.js
const { SlashCommandBuilder, PermissionFlagsBits, EmbedBuilder } = require('discord.js');

async function sendLog(guild, embed) {
  const logCh = guild.channels.cache.find(c => c.name.includes('mod-log') && c.isTextBased());
  if (logCh) await logCh.send({ embeds: [embed] }).catch(() => {});
}

module.exports = {
  data: new SlashCommandBuilder()
    .setName('mod')
    .setDescription('🛡️ Moderation commands')
    .setDefaultMemberPermissions(PermissionFlagsBits.ModerateMembers)
    .addSubcommand(s => s.setName('warn').setDescription('⚠️ Warn a member')
      .addUserOption(o => o.setName('user').setDescription('Member to warn').setRequired(true))
      .addStringOption(o => o.setName('reason').setDescription('Reason').setRequired(false)))
    .addSubcommand(s => s.setName('timeout').setDescription('⏱️ Timeout a member')
      .addUserOption(o => o.setName('user').setDescription('Member to timeout').setRequired(true))
      .addIntegerOption(o => o.setName('minutes').setDescription('Duration in minutes').setRequired(true).setMinValue(1).setMaxValue(40320))
      .addStringOption(o => o.setName('reason').setDescription('Reason').setRequired(false)))
    .addSubcommand(s => s.setName('kick').setDescription('👢 Kick a member')
      .addUserOption(o => o.setName('user').setDescription('Member to kick').setRequired(true))
      .addStringOption(o => o.setName('reason').setDescription('Reason').setRequired(false)))
    .addSubcommand(s => s.setName('ban').setDescription('🔨 Ban a member')
      .addUserOption(o => o.setName('user').setDescription('Member to ban').setRequired(true))
      .addStringOption(o => o.setName('reason').setDescription('Reason').setRequired(false)))
    .addSubcommand(s => s.setName('unban').setDescription('✅ Unban a user')
      .addStringOption(o => o.setName('userid').setDescription('User ID').setRequired(true)))
    .addSubcommand(s => s.setName('purge').setDescription('🗑️ Delete messages')
      .addIntegerOption(o => o.setName('amount').setDescription('Number of messages (1-100)').setRequired(true).setMinValue(1).setMaxValue(100))),

  async execute(interaction) {
    const sub    = interaction.options.getSubcommand();
    const guild  = interaction.guild;
    const mod    = interaction.user;

    if (sub === 'purge') {
      const amount = interaction.options.getInteger('amount');
      await interaction.channel.bulkDelete(amount, true);
      await interaction.reply({ content: `✅ Deleted ${amount} messages.`, ephemeral: true });
      return;
    }

    if (sub === 'unban') {
      const userId = interaction.options.getString('userid');
      await guild.members.unban(userId).catch(() => {});
      await interaction.reply({ content: `✅ Unbanned user \`${userId}\`.`, ephemeral: true });
      return;
    }

    const target = interaction.options.getMember('user');
    const reason = interaction.options.getString('reason') || 'No reason provided';

    if (!target) {
      await interaction.reply({ content: '❌ Member not found.', ephemeral: true });
      return;
    }

    const colors = { warn: 0xFBBF24, timeout: 0xF97316, kick: 0xEF4444, ban: 0x991B1B };
    const icons  = { warn: '⚠️', timeout: '⏱️', kick: '👢', ban: '🔨' };

    let actionText = '';

    if (sub === 'warn') {
      actionText = 'Warned';
      try {
        await target.send({
          embeds: [new EmbedBuilder()
            .setColor(0xFBBF24)
            .setTitle(`⚠️ You were warned in ${guild.name}`)
            .addFields({ name: 'Reason', value: reason })
            .setTimestamp()
          ]
        });
      } catch {}
    }

    if (sub === 'timeout') {
      const minutes = interaction.options.getInteger('minutes');
      await target.timeout(minutes * 60 * 1000, reason);
      actionText = `Timed out for ${minutes} minutes`;
    }

    if (sub === 'kick') {
      await target.kick(reason);
      actionText = 'Kicked';
    }

    if (sub === 'ban') {
      await target.ban({ reason, deleteMessageSeconds: 86400 });
      actionText = 'Banned';
    }

    const embed = new EmbedBuilder()
      .setColor(colors[sub])
      .setTitle(`${icons[sub]} Member ${actionText}`)
      .setThumbnail(target.user.displayAvatarURL({ dynamic: true }))
      .addFields(
        { name: '👤 Member', value: `${target.user.tag}`, inline: true },
        { name: '🛡️ Moderator', value: `${mod.tag}`, inline: true },
        { name: '📝 Reason', value: reason, inline: false },
      )
      .setTimestamp();

    await sendLog(guild, embed);
    await interaction.reply({ embeds: [embed], ephemeral: true });
  }
};
