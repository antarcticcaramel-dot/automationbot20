// src/events/messageCreate.js
const { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');

const countingState = { count: 0, lastUserId: null };

module.exports = {
  name: 'messageCreate',
  async execute(message, client) {
    if (message.author.bot) return;

    const channelName = message.channel.name?.toLowerCase() || '';

    // ── 🎨 Art Channel ────────────────────────────────────────────────────────
    if (channelName.includes('art')) {
      const images = message.attachments.filter(a =>
        a.contentType?.startsWith('image/') || a.url?.match(/\.(png|jpg|jpeg|gif|webp)$/i)
      );

      if (images.size === 0) {
        await message.delete().catch(() => {});
        try {
          await message.author.send({
            embeds: [new EmbedBuilder()
              .setColor(0xF472B6)
              .setTitle('🎨 Art Channel — Images Only!')
              .setDescription('The **art channel** only allows image posts.\nAttach an image to share your artwork! 🖼️')
              .setFooter({ text: 'Use #general for text chat' })
            ]
          });
        } catch {}
        return;
      }

      const caption = message.content?.trim() || null;
      await message.delete().catch(() => {});

      // Repost every image as its own embed
      for (const [, attachment] of images) {
        const artEmbed = new EmbedBuilder()
          .setColor(0xA855F7)
          .setAuthor({
            name: `🎨 ${message.member?.displayName || message.author.username}'s Artwork`,
            iconURL: message.author.displayAvatarURL({ dynamic: true })
          })
          .setImage(attachment.url)
          .setTimestamp()
          .setFooter({ text: '👍 Like it? Hit the button below!' });

        if (caption) artEmbed.setDescription(`*"${caption}"*`);

        const ts = Date.now();
        const row = new ActionRowBuilder().addComponents(
          new ButtonBuilder()
            .setCustomId(`art_like_${message.author.id}_${ts}`)
            .setLabel('0')
            .setEmoji('👍')
            .setStyle(ButtonStyle.Success),
          new ButtonBuilder()
            .setCustomId(`art_dislike_${message.author.id}_${ts}`)
            .setLabel('0')
            .setEmoji('👎')
            .setStyle(ButtonStyle.Danger),
          new ButtonBuilder()
            .setCustomId(`art_share_${message.author.id}_${ts}`)
            .setLabel('Share')
            .setEmoji('🔗')
            .setStyle(ButtonStyle.Secondary)
        );

        await message.channel.send({
          content: `> 🎨 Artwork posted by ${message.author}`,
          embeds: [artEmbed],
          components: [row]
        });
      }
      return;
    }

    // ── 💡 Suggestions Channel ────────────────────────────────────────────────
    if (channelName.includes('suggestion')) {
      if (message.content.length < 10) {
        await message.delete().catch(() => {});
        try {
          await message.author.send({
            embeds: [new EmbedBuilder()
              .setColor(0xFBBF24)
              .setTitle('💡 Suggestion Too Short')
              .setDescription('Please write a more detailed suggestion (at least 10 characters).')
            ]
          });
        } catch {}
        return;
      }

      const suggestionText = message.content;
      await message.delete().catch(() => {});

      const ts = Date.now();
      const suggEmbed = new EmbedBuilder()
        .setColor(0xFBBF24)
        .setTitle('💡 New Suggestion')
        .setDescription(`>>> ${suggestionText}`)
        .addFields(
          { name: '👤 Submitted by', value: `${message.author}`, inline: true },
          { name: '📊 Status', value: '🕐 Pending Review', inline: true },
          { name: '📈 Votes', value: '⬆️ **0** — ⬇️ **0** — ➡️ **0**', inline: false }
        )
        .setThumbnail(message.author.displayAvatarURL({ dynamic: true }))
        .setTimestamp()
        .setFooter({ text: 'Vote below to support this suggestion!' });

      const row = new ActionRowBuilder().addComponents(
        new ButtonBuilder()
          .setCustomId(`sugg_upvote_${message.author.id}_${ts}`)
          .setLabel('0  Upvote')
          .setEmoji('⬆️')
          .setStyle(ButtonStyle.Success),
        new ButtonBuilder()
          .setCustomId(`sugg_downvote_${message.author.id}_${ts}`)
          .setLabel('0  Downvote')
          .setEmoji('⬇️')
          .setStyle(ButtonStyle.Danger),
        new ButtonBuilder()
          .setCustomId(`sugg_neutral_${message.author.id}_${ts}`)
          .setLabel('0  Neutral')
          .setEmoji('➡️')
          .setStyle(ButtonStyle.Secondary)
      );

      await message.channel.send({ embeds: [suggEmbed], components: [row] });
      return;
    }

    // ── 🔢 Counting Channel ───────────────────────────────────────────────────
    if (channelName.includes('counting')) {
      const num = parseInt(message.content.trim());
      const expected = countingState.count + 1;

      if (isNaN(num) || num !== expected || message.author.id === countingState.lastUserId) {
        await message.delete().catch(() => {});
        const reason = message.author.id === countingState.lastUserId
          ? "You can't count twice in a row!"
          : `Wrong number! Expected **${expected}**.`;
        const warn = await message.channel.send({
          embeds: [new EmbedBuilder()
            .setColor(0xEF4444)
            .setDescription(`❌ ${message.author} — ${reason} Count reset to **0**.`)
          ]
        });
        countingState.count = 0;
        countingState.lastUserId = null;
        setTimeout(() => warn.delete().catch(() => {}), 5000);
        return;
      }

      countingState.count = num;
      countingState.lastUserId = message.author.id;
      await message.react(num % 100 === 0 ? '🎉' : '✅').catch(() => {});
      return;
    }

    // ── 📣 Self-promote Channel ───────────────────────────────────────────────
    if (channelName.includes('self-promote') || channelName.includes('selfpromote')) {
      await message.react('👀').catch(() => {});
      return;
    }
  }
};
