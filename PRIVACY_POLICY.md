# Privacy Policy

**Last updated: June 1, 2026**

This Privacy Policy describes how the operator of this SMS AI Chatbot ("the Bot", "we", "us") collects, uses, stores, and protects information when you interact with the Bot by sending SMS messages to its configured phone number.

> **Note for operators:** This is a template. Replace all `[BRACKETED PLACEHOLDERS]` with your actual information before publishing or deploying.

---

## 1. Who This Policy Applies To

This policy applies to anyone who sends an SMS message to a phone number operated by **[OPERATOR NAME / YOUR NAME OR BUSINESS]** using this software. By texting the Bot, you acknowledge this policy.

---

## 2. Information We Collect

When you send a text message to the Bot, the following information is automatically collected and stored locally on the server running the Bot:

| Data | What It Is | Where It Is Stored |
|---|---|---|
| **Phone number** | Your mobile phone number in E.164 format (e.g. `+15551234567`) | Contact files (`contacts/`) and conversation logs (`logs/`) |
| **Message content** | The full text of every message you send and every reply the Bot sends | Conversation logs (`logs/chat.log`) |
| **Extracted facts** | Personal details the AI automatically infers from your messages (e.g. your name, occupation, interests, upcoming events) | Contact files (`contacts/<your-number>.txt`) |
| **Conversation history** | A rolling window of recent messages used to maintain context | In memory only; cleared after a configurable period of inactivity (default: 24 hours) |

We do **not** collect payment information, device identifiers, IP addresses, or any data beyond what is listed above.

---

## 3. How We Use Your Information

Your information is used solely to:

- Generate contextually relevant AI replies to your messages
- Maintain continuity across a conversation session
- Personalize responses over time by remembering facts you share

Your data is **not** used for advertising, sold to third parties, or shared with anyone outside of the services described in Section 5.

---

## 4. Data Storage and Retention

All data is stored **locally on the server** operated by **[OPERATOR NAME]**. There is no centralized database.

- **Conversation history** — held in memory and cleared automatically after **[X hours]** of inactivity (default: 24 hours).
- **Contact files** — retained indefinitely until manually deleted by the operator or until you request deletion.
- **Log files** — written to daily rotating files in `logs/`. Retention period is determined by the operator's server configuration.

The operator is solely responsible for securing the server, the `.env` credentials file, the `contacts/` directory, and the `logs/` directory. These directories are excluded from version control by default (`.gitignore`) to prevent accidental exposure.

---

## 5. Third-Party Services

The Bot relies on the following third-party services to function. When you send a message, your phone number and message content are transmitted to these services as described:

### Vonage (SMS Delivery)
Your phone number and message content pass through Vonage's network for SMS delivery and receipt. Vonage acts as the carrier interface. Their data practices are governed by the [Vonage Privacy Policy](https://www.vonage.com/legal/privacy-policy/).

### Groq (AI Inference)
Your message content and recent conversation history are sent to Groq's API to generate a reply. Groq processes this data to produce an AI response. Their data practices are governed by the [Groq Privacy Policy](https://groq.com/privacy-policy/).

We do not control how these third parties store or process data once it is transmitted to them. You should review their privacy policies if you have concerns.

---

## 6. Your Rights and Controls

You have the following controls over your data:

- **Reset your history** — Text `reset` to the Bot at any time. This immediately clears your conversation history from memory. It does not delete your contact file or log entries.
- **Request deletion** — Contact the operator at **[CONTACT EMAIL]** to request deletion of your contact file or log entries associated with your phone number.
- **Opt out** — Stop texting the Bot number at any time. No further data will be collected.

If you are located in a jurisdiction with additional data rights (e.g., GDPR, CCPA), you may have further rights including access, portability, and the right to object. Contact **[CONTACT EMAIL]** to exercise these rights.

---

## 7. Security

The operator is responsible for securing the server environment. Recommended protections include:

- Setting `VONAGE_SIGNATURE_SECRET` to enable HMAC webhook verification, which rejects spoofed inbound requests
- Restricting server access via firewall rules
- Keeping credentials in `.env` (never committed to version control)
- Using `ALLOWED_NUMBERS` in `config.py` to limit who the Bot responds to

We cannot guarantee absolute security of any system. Use this software in accordance with your own security requirements.

---

## 8. Children's Privacy

This Bot is not intended for use by individuals under the age of 13 (or the applicable age of digital consent in your jurisdiction). We do not knowingly collect information from minors. If you believe a minor has used this service, contact **[CONTACT EMAIL]** immediately.

---

## 9. Changes to This Policy

We may update this policy from time to time. The "Last updated" date at the top of this document will reflect any changes. Continued use of the Bot after changes are posted constitutes acceptance of the updated policy.

---

## 10. Contact

For questions, data deletion requests, or privacy concerns, contact:

**[OPERATOR NAME]**
**[CONTACT EMAIL]**
**[OPTIONAL: WEBSITE / GITHUB URL]**
