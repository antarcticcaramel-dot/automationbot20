// src/events/guildMemberUpdate.js
const { EmbedBuilder } = require('discord.js');

module.exports = {
  name: 'guildMemberUpdate',
  async execute(oldMember, newMember, client) {
    const guild = newMember.guild;

    // ── Detect Server Boost ───────────────────────────────────────────────────
    const wasBooster = oldMember.premiumSince;
    const isBooster  = newMember.premiumSince;

    if (!wasBooster && isBooster) {
      // New boost!
      const boostChannel =
        guild.channels.cache.find(c => c.name.includes('boosts') && c.isTextBased()) ||
        guild.channels.cache.find(c => c.name.includes('general') && c.isTextBased());

      if (boostChannel) {
        const embed = new EmbedBuilder()
          .setColor(0xF472B6)
          .setTitle('🚀 Server Boosted!')
          .setDescription([
            `## ${newMember} just boosted the server! 💎`,
            ``,
            `Thank you so much for your support! ❤️`,
            `You're helping us unlock amazing perks for everyone.`,
            ``,
            `**Current Boost Level:** ${guild.premiumTier === 0 ? 'No Level' : `Level ${guild.premiumTier}`}`,
            `**Total Boosts:** ${guild.premiumSubscriptionCount} 🚀`,
          ].join('\n'))
          .setThumbnail(newMember.user.displayAvatarURL({ dynamic: true, size: 256 }))
          // Official Discord Nitro Boost image
          .setImage('https://media.discordapp.net/attachments/1078231423286566932/1160547419297595452/boost.png?ex=6534a4de&is=65222fde&hm=7aafd94e21e80e0ec32ec57abcea84a39c3ce18bc2c40c72e4a1e7b4ead1a3a2&=&width=900&height=500')
          .setTimestamp()
          .setFooter({ text: `${guild.name} • Thanks for boosting! 💖`, iconURL: guild.iconURL({ dynamic: true }) });

        await boostChannel.send({
          content: `> 🌟 ${newMember} just became a Server Booster!`,
          embeds: [embed]
        });
      }

      // Give Booster role
      const boosterRole = guild.roles.cache.find(r => r.name.includes('Booster'));
      if (boosterRole) await newMember.roles.add(boosterRole).catch(() => {});
      const supporterRole = guild.roles.cache.find(r => r.name.includes('Supporter'));
      if (supporterRole) await newMember.roles.add(supporterRole).catch(() => {});
    }

    // ── Supporter Role Sync ───────────────────────────────────────────────────
    // If someone gains the Supporter role, log it
    const gainedRoles = newMember.roles.cache.filter(r => !oldMember.roles.cache.has(r.id));
    gainedRoles.forEach(async role => {
      if (role.name.includes('Supporter')) {
        const accessCh = guild.channels.cache.find(c => c.name.includes('access') && c.isTextBased());
        if (accessCh) {
          await accessCh.send({
            embeds: [new EmbedBuilder()
              .setColor(0xA855F7)
              .setDescription(`✨ Welcome to the **Supporters** section, ${newMember}! You now have access to all exclusive perks. 💎`)
            ]
          });
        }
      }
    });
  }
};
