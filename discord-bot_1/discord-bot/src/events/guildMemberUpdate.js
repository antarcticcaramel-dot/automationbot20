// src/events/guildMemberUpdate.js
const { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');

const DISCORD_INVITE = 'https://discord.gg/CZ28Gh3wXG';
const ROBLOX_GROUP   = 'https://www.roblox.com/share/g/35116281';

module.exports = {
  name: 'guildMemberUpdate',
  async execute(oldMember, newMember, client) {
    const guild = newMember.guild;

    // ── Detect Server Boost ───────────────────────────────────────────────────
    const wasBooster = oldMember.premiumSince;
    const isBooster  = newMember.premiumSince;

    if (!wasBooster && isBooster) {
      const boostChannel =
        guild.channels.cache.find(c => c.name.includes('boost') && c.isTextBased()) ||
        guild.channels.cache.find(c => c.name.includes('general') && c.isTextBased());

      if (boostChannel) {
        const embed = new EmbedBuilder()
          .setColor(0xF472B6)
          .setTitle('🚀 THE SERVER HAS BEEN BOOSTED!')
          .setDescription([
            `## ${newMember} just boosted the server! 🎉`,
            '',
            '**Thank you SO much for your support!** 💖',
            'You\'re helping us grow and unlock incredible perks for everyone.',
            '',
            '**🎁 Your Booster Perks:**',
            '• 💎 Full Supporter section access',
            '• 👑 VIP Chat & Voice channel',
            '• 🎨 Custom colour role (ask staff)',
            '• 🌟 Highlighted at the top of the member list',
            '• 📣 This shoutout — you\'re a legend!',
            '',
            `**Current Level:** ${guild.premiumTier === 0 ? 'No Level yet' : `Level ${guild.premiumTier} 🏆`}`,
            `**Total Boosts:** ${'🚀'.repeat(Math.min(guild.premiumSubscriptionCount, 10))} (${guild.premiumSubscriptionCount})`,
          ].join('\n'))
          .setThumbnail(newMember.user.displayAvatarURL({ dynamic: true, size: 256 }))
          .setImage('https://media.discordapp.net/attachments/858992969651961876/1073249983542800395/boost.gif')
          .setTimestamp()
          .setFooter({ text: `${guild.name} • We appreciate you so much 💜`, iconURL: guild.iconURL({ dynamic: true }) });

        const row = new ActionRowBuilder().addComponents(
          new ButtonBuilder().setLabel('Join Discord').setEmoji('💬').setStyle(ButtonStyle.Link).setURL(DISCORD_INVITE),
          new ButtonBuilder().setLabel('Roblox Group').setEmoji('🎮').setStyle(ButtonStyle.Link).setURL(ROBLOX_GROUP),
        );

        await boostChannel.send({
          content: `> 🌟 @everyone — ${newMember} just boosted the server! Give them some love! 💖`,
          embeds: [embed],
          components: [row]
        });
      }

      // Give Booster + Supporter roles
      const boosterRole  = guild.roles.cache.find(r => r.name.toLowerCase().includes('booster') && !r.managed);
      const supporterRole = guild.roles.cache.find(r => r.name.toLowerCase().includes('supporter'));
      if (boosterRole)   await newMember.roles.add(boosterRole).catch(() => {});
      if (supporterRole) await newMember.roles.add(supporterRole).catch(() => {});

      // DM the booster
      try {
        await newMember.send({
          embeds: [new EmbedBuilder()
            .setColor(0xF472B6)
            .setTitle('🚀 Thank you for boosting!')
            .setDescription([
              `You just boosted **${guild.name}** — you absolute legend! 💖`,
              '',
              '**Your perks are now active:**',
              '• 💎 Supporter section access',
              '• 👑 VIP Chat & Voice',
              '• 🎨 Ask a staff member for a custom colour role',
              '',
              'Use `/perks` in the server to see everything you unlocked!',
            ].join('\n'))
            .setTimestamp()
          ]
        });
      } catch {}

      // Welcome in supporters access channel
      const accessCh = guild.channels.cache.find(c => c.name.includes('access') && c.isTextBased());
      if (accessCh) {
        await accessCh.send({
          embeds: [new EmbedBuilder()
            .setColor(0xF472B6)
            .setTitle('🚀 New Booster in the Building!')
            .setDescription(`Welcome ${newMember} to the exclusive supporters section! You boosted the server and you deserve every perk. Thank you! 💜`)
            .setThumbnail(newMember.user.displayAvatarURL({ dynamic: true }))
            .setTimestamp()
          ]
        });
      }
    }

    // ── Supporter Role Granted ────────────────────────────────────────────────
    const gainedRoles = newMember.roles.cache.filter(r => !oldMember.roles.cache.has(r.id));
    for (const [, role] of gainedRoles) {
      if (role.name.toLowerCase().includes('supporter') && !newMember.premiumSince) {
        const accessCh = guild.channels.cache.find(c => c.name.includes('access') && c.isTextBased());
        if (accessCh) {
          await accessCh.send({
            embeds: [new EmbedBuilder()
              .setColor(0xA855F7)
              .setTitle('💎 New Supporter!')
              .setDescription([
                `Welcome ${newMember} to the **Supporters** family! 💜`,
                '',
                '**Your perks are now active:**',
                '• 👑 VIP Chat & Voice access',
                '• 📢 Early access to announcements',
                '• 💜 Priority staff support',
                '',
                'Use `/perks` to see everything you have access to!',
              ].join('\n'))
              .setThumbnail(newMember.user.displayAvatarURL({ dynamic: true }))
              .setTimestamp()
            ]
          });
        }

        // DM the new supporter
        try {
          await newMember.send({
            embeds: [new EmbedBuilder()
              .setColor(0xA855F7)
              .setTitle('💎 Welcome to Supporters!')
              .setDescription([
                `You've been granted the **Supporter** role in **${guild.name}**! 🎉`,
                '',
                'You now have access to exclusive channels and perks.',
                'Use `/perks` in the server to see everything!',
              ].join('\n'))
              .setTimestamp()
            ]
          });
        } catch {}
      }
    }
  }
};
