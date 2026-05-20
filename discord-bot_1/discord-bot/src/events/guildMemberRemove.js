// src/events/guildMemberRemove.js
const { EmbedBuilder } = require('discord.js');

module.exports = {
  name: 'guildMemberRemove',
  async execute(member, client) {
    const guild = member.guild;
    const logChannel = guild.channels.cache.find(c => c.name.includes('server-log') && c.isTextBased());
    if (!logChannel) return;

    const embed = new EmbedBuilder()
      .setColor(0xEF4444)
      .setTitle('👋 Member Left')
      .setThumbnail(member.user.displayAvatarURL({ dynamic: true }))
      .addFields(
        { name: '👤 User', value: `${member.user.tag}`, inline: true },
        { name: '🆔 ID', value: member.user.id, inline: true },
        { name: '📅 Joined', value: member.joinedAt ? `<t:${Math.floor(member.joinedAt / 1000)}:R>` : 'Unknown', inline: true },
        { name: '🎭 Roles', value: member.roles.cache.filter(r => r.name !== '@everyone').map(r => r.name).join(', ') || 'None', inline: false }
      )
      .setTimestamp()
      .setFooter({ text: `${guild.memberCount} members remaining` });

    await logChannel.send({ embeds: [embed] });
  }
};
