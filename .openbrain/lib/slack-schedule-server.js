#!/usr/bin/env node
// Minimal MCP server for chat.scheduleMessage — no npm dependencies.
// Implements MCP JSON-RPC 2.0 over stdio using only Node.js built-ins.

import { createInterface } from "readline";
import https from "https";

const TOKEN = process.env.SLACK_MCP_XOXP_TOKEN;
if (!TOKEN) {
  process.stderr.write("slack-schedule-mcp: SLACK_MCP_XOXP_TOKEN not set\n");
  process.exit(1);
}

function slackPost(method, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const req = https.request(
      {
        hostname: "slack.com",
        path: `/api/${method}`,
        method: "POST",
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          Authorization: `Bearer ${TOKEN}`,
          "Content-Length": Buffer.byteLength(data),
        },
      },
      (res) => {
        let raw = "";
        res.on("data", (c) => (raw += c));
        res.on("end", () => {
          try {
            const p = JSON.parse(raw);
            if (!p.ok) reject(new Error(p.error || "slack error"));
            else resolve(p);
          } catch (e) {
            reject(e);
          }
        });
      }
    );
    req.on("error", reject);
    req.write(data);
    req.end();
  });
}

function send(msg) {
  process.stdout.write(JSON.stringify(msg) + "\n");
}

const TOOL = {
  name: "slack_schedule_message",
  description:
    "Schedule a Slack message to be sent at a future time using chat.scheduleMessage.",
  inputSchema: {
    type: "object",
    properties: {
      channel: {
        type: "string",
        description: "Channel ID, #channel-name, or @username for DMs",
      },
      text: {
        type: "string",
        description: "Message text (Slack mrkdwn supported)",
      },
      post_at: {
        type: "string",
        description:
          "When to send. ISO 8601 datetime (e.g. '2026-04-22T17:00:00-04:00') or Unix timestamp string.",
      },
      thread_ts: {
        type: "string",
        description:
          "Parent message timestamp to schedule a reply in a thread (optional)",
      },
    },
    required: ["channel", "text", "post_at"],
  },
};

const rl = createInterface({ input: process.stdin, terminal: false });

rl.on("line", async (line) => {
  const trimmed = line.trim();
  if (!trimmed) return;

  let msg;
  try {
    msg = JSON.parse(trimmed);
  } catch {
    return;
  }

  if (msg.method === "initialize") {
    send({
      jsonrpc: "2.0",
      id: msg.id,
      result: {
        protocolVersion: "2024-11-05",
        capabilities: { tools: {} },
        serverInfo: { name: "slack-schedule-mcp", version: "1.0.0" },
      },
    });
  } else if (msg.method === "notifications/initialized") {
    // notification — no response
  } else if (msg.method === "tools/list") {
    send({ jsonrpc: "2.0", id: msg.id, result: { tools: [TOOL] } });
  } else if (msg.method === "tools/call") {
    const { name, arguments: args } = msg.params;
    if (name !== "slack_schedule_message") {
      send({
        jsonrpc: "2.0",
        id: msg.id,
        error: { code: -32601, message: `Unknown tool: ${name}` },
      });
      return;
    }
    try {
      const { channel, text, post_at, thread_ts } = args;

      // Parse post_at → Unix seconds
      let postAtTs;
      if (/^\d+$/.test(String(post_at))) {
        postAtTs = parseInt(post_at, 10);
      } else {
        const d = new Date(post_at);
        if (isNaN(d.getTime())) throw new Error(`Invalid post_at value: ${post_at}`);
        postAtTs = Math.floor(d.getTime() / 1000);
      }

      // Must be in the future
      if (postAtTs <= Math.floor(Date.now() / 1000)) {
        throw new Error("post_at must be in the future");
      }

      const body = { channel, text, post_at: postAtTs };
      if (thread_ts) body.thread_ts = thread_ts;

      const r = await slackPost("chat.scheduleMessage", body);

      const sendTime = new Date(postAtTs * 1000).toLocaleString("en-US", {
        timeZone: "America/New_York",
        dateStyle: "medium",
        timeStyle: "short",
      });

      send({
        jsonrpc: "2.0",
        id: msg.id,
        result: {
          content: [
            {
              type: "text",
              text: `Scheduled — ID: ${r.scheduled_message_id}\nChannel: ${r.channel}\nSends at: ${sendTime} ET`,
            },
          ],
        },
      });
    } catch (e) {
      send({
        jsonrpc: "2.0",
        id: msg.id,
        result: {
          content: [{ type: "text", text: `Error: ${e.message}` }],
          isError: true,
        },
      });
    }
  } else if (msg.id != null) {
    send({
      jsonrpc: "2.0",
      id: msg.id,
      error: { code: -32601, message: `Method not found: ${msg.method}` },
    });
  }
});
