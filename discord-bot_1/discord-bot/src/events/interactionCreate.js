// src/events/interactionCreate.js
const { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');

// In-memory vote tracking (resets on restart — fine for most servers)
const voteMap = new Map();

module.exports = {
  name: 'interactionCreate',
  async execute(interaction, client) {

    // ── Slash Commands ────────────────────────────────────────────────────────
    if (interaction.isChatInputCommand()) {
      const command = client.commands.get(interaction.commandName);
      if (!command) return;
      try {
        await command.execute(interaction, client);
      } catch (err) {
        console.error(`Error in command ${interaction.commandName}:`, err);
        const reply = { content: '❌ Something went wrong.', ephemeral: true };
        interaction.replied ? interaction.followUp(reply) : interaction.reply(reply);
      }
      return;
    }

    // ── Buttons ───────────────────────────────────────────────────────────────
    if (!interaction.isButton()) return;
    const id = interaction.customId;

    // ── Art Like/Dislike ──────────────────────────────────────────────────────
    if (id.startsWith('art_like_') || id.startsWith('art_dislike_') || id.startsWith('art_share_')) {
      const msgId = interaction.message.id;
      if (!voteMap.has(msgId)) voteMap.set(msgId, { likes: new Set(), dislikes: new Set() });
      const votes = voteMap.get(msgId);

      if (id.startsWith('art_share_')) {
        await interaction.reply({
          content: `🔗 Share this artwork: ${interaction.message.url}`,
          ephemeral: true
        });
        return;
      }

      const userId = interaction.user.id;
      const isLike = id.startsWith('art_like_');

      if (isLike) {
        if (votes.likes.has(userId)) {
          votes.likes.delete(userId);
        } else {
          votes.likes.add(userId);
          votes.dislikes.delete(userId);
        }
      } else {
        if (votes.dislikes.has(userId)) {
          votes.dislikes.delete(userId);
        } else {
          votes.dislikes.add(userId);
          votes.likes.delete(userId);
        }
      }

      const artistId = id.split('_')[2];
      const row = new ActionRowBuilder().addComponents(
        new ButtonBuilder()
          .setCustomId(`art_like_${artistId}`)
          .setLabel(`${votes.likes.size}`)
          .setEmoji('👍')
          .setStyle(ButtonStyle.Success),
        new ButtonBuilder()
          .setCustomId(`art_dislike_${artistId}`)
          .setLabel(`${votes.dislikes.size}`)
          .setEmoji('👎')
          .setStyle(ButtonStyle.Danger),
        new ButtonBuilder()
          .setCustomId(`art_share_${artistId}`)
          .setLabel('Share')
          .setEmoji('🔗')
          .setStyle(ButtonStyle.Secondary)
      );

      await interaction.update({ components: [row] });
      return;
    }

    // ── Suggestion Votes ──────────────────────────────────────────────────────
    if (id.startsWith('sugg_')) {
      const msgId = interaction.message.id;
      if (!voteMap.has(msgId)) voteMap.set(msgId, { up: new Set(), down: new Set(), neutral: new Set() });
      const votes = voteMap.get(msgId);
      const userId = interaction.user.id;

      const type = id.split('_')[1]; // upvote / downvote / neutral
      ['up','down','neutral'].forEach(k => votes[k].delete(userId));

      if (type === 'upvote')   votes.up.add(userId);
      if (type === 'downvote') votes.down.add(userId);
      if (type === 'neutral')  votes.neutral.add(userId);

      const total = votes.up.size + votes.down.size + votes.neutral.size;
      const pct = (n) => total ? Math.round((n / total) * 100) : 0;
      const bar = (n) => '█'.repeat(Math.round(pct(n) / 10)) + '░'.repeat(10 - Math.round(pct(n) / 10));

      // Update embed status color based on votes
      const embed = EmbedBuilder.from(interaction.message.embeds[0])
        .setColor(votes.up.size > votes.down.size ? 0x22C55E : votes.down.size > votes.up.size ? 0xEF4444 : 0xFBBF24)
        .spliceFields(1, 1, {
          name: '📊 Status',
          value: votes.up.size > votes.down.size ? '✅ Trending Positive' : votes.down.size > votes.up.size ? '❌ Trending Negative' : '🕐 Pending Review',
          inline: true
        })
        .addFields({
          name: `📊 Votes — ${total} total`,
          value: [
            `⬆️ **${votes.up.size}** — ${bar(votes.up.size)} ${pct(votes.up.size)}%`,
            `⬇️ **${votes.down.size}** — ${bar(votes.down.size)} ${pct(votes.down.size)}%`,
            `➡️ **${votes.neutral.size}** — ${bar(votes.neutral.size)} ${pct(votes.neutral.size)}%`,
          ].join('\n')
        });

      const parts = id.split('_');
      const authorId = parts[2];
      const ts = parts[3];
      const row = new ActionRowBuilder().addComponents(
        new ButtonBuilder().setCustomId(`sugg_upvote_${authorId}_${ts}`).setLabel(`${votes.up.size}  Upvote`).setEmoji('⬆️').setStyle(ButtonStyle.Success),
        new ButtonBuilder().setCustomId(`sugg_downvote_${authorId}_${ts}`).setLabel(`${votes.down.size}  Downvote`).setEmoji('⬇️').setStyle(ButtonStyle.Danger),
        new ButtonBuilder().setCustomId(`sugg_neutral_${authorId}_${ts}`).setLabel(`${votes.neutral.size}  Neutral`).setEmoji('➡️').setStyle(ButtonStyle.Secondary),
      );

      await interaction.update({ embeds: [embed], components: [row] });
      return;
    }

    // ── Self-Role Buttons ─────────────────────────────────────────────────────
    if (id.startsWith('selfrole_')) {
      const roleId = id.replace('selfrole_', '');
      const member = interaction.member;
      const role = interaction.guild.roles.cache.get(roleId);

      if (!role) {
        await interaction.reply({ content: '❌ Role not found. Contact an admin.', ephemeral: true });
        return;
      }

      if (member.roles.cache.has(roleId)) {
        await member.roles.remove(role);
        await interaction.reply({
          embeds: [new EmbedBuilder()
            .setColor(0xEF4444)
            .setDescription(`✅ Removed the **${role.name}** role from you.`)
          ],
          ephemeral: true
        });
      } else {
        await member.roles.add(role);
        await interaction.reply({
          embeds: [new EmbedBuilder()
            .setColor(0x22C55E)
            .setDescription(`✅ You now have the **${role.name}** role!`)
          ],
          ephemeral: true
        });
      }
      return;
    }
  }
};
