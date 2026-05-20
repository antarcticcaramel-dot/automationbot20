// src/events/guildMemberAdd.js
const { EmbedBuilder } = require('discord.js');

module.exports = {
  name: 'guildMemberAdd',
  async execute(member, client) {
    const guild = member.guild;

    // ── Find a dedicated welcome channel first ────────────────────────────────
    const welcomeChannel =
      guild.channels.cache.find(c => c.name.includes('welcome') && c.isTextBased()) ||
      guild.systemChannel;

    if (!welcomeChannel) return;

    const memberCount = guild.memberCount;
    const ordinal = (n) => {
      const s = ['th','st','nd','rd'], v = n % 100;
      return n + (s[(v - 20) % 10] || s[v] || s[0]);
    };

    const selfRolesChannel = guild.channels.cache.find(c => c.name.includes('self-role'));
    const announcementsChannel = guild.channels.cache.find(c => c.name.includes('announcement'));
    const generalChannel = guild.channels.cache.find(c => c.name.includes('general') && c.isTextBased());

    const embed = new EmbedBuilder()
      .setColor(0xA855F7)
      .setTitle('✨ Welcome to the Server!')
      .setDescription([
        `## Hey ${member}, welcome to **${guild.name}**! 🎉`,
        ``,
        `You are our **${ordinal(memberCount)}** member — we're so glad you're here!`,
        ``,
        `**📌 Start here:**`,
        selfRolesChannel   ? `• 🎭 ${selfRolesChannel} — grab your roles` : '',
        announcementsChannel ? `• 📢 ${announcementsChannel} — stay updated` : '',
        generalChannel     ? `• 💬 ${generalChannel} — say hi!` : '',
        ``,
        `Hope you enjoy your stay! 💜`,
      ].filter(Boolean).join('\n'))
      .setThumbnail(member.user.displayAvatarURL({ dynamic: true, size: 256 }))
      .setTimestamp()
      .setFooter({ text: `${guild.name} • Member #${memberCount}`, iconURL: guild.iconURL({ dynamic: true }) });

    await welcomeChannel.send({ content: `> 👋 Everyone say hello to ${member}!`, embeds: [embed] });

    // Auto-assign Member role
    const memberRole = guild.roles.cache.find(r => r.name.toLowerCase().includes('member') && !r.managed);
    if (memberRole) await member.roles.add(memberRole).catch(() => {});
  }
};
