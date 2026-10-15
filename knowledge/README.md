# Knowledge folder

Everything in this folder is what your chatbot knows. Each `.txt` file is turned into one searchable entry by `python embed.py`. The bot answers only from these files, so if something isn't written here, the bot won't know it.

> This README is a `.md` file on purpose. Only `.txt` files are read by the chatbot.

## What to add

Create your own `.txt` files in this folder. Suggested files:

| File (suggested name) | What to put in it |
|---|---|
| `about.txt` | Who you are, what you do, when you started, where you're based |
| `services.txt` | Each service or product with a one or two sentence description |
| `contact.txt` | Email, phone, addresses, business hours, links to your contact form |
| `faq.txt` | The questions customers ask most, with the answers you want given |
| `process.txt` | How working with you goes, step by step |
| `portfolio.txt` | Past projects, clients or results you're happy to mention |
| `pricing.txt` | Only if you want the bot to share pricing. Otherwise leave it out and the bot will send people to your team |
| `policies.txt` | Returns, refunds, privacy, terms, support hours |

You don't need all of them. Start with `about`, `services`, `contact` and `faq`.

## How to write good files

1. **One topic per file.** Mixed files give vague matches.
2. **100 to 300 words per file.** Split anything longer into several files.
3. **Plain sentences.** Write the way a visitor would ask: "How do I contact you?"
4. **Include names and keywords** visitors will use: service names, city names, product names.
5. **Only include what you're happy to say publicly.** Anything here can end up in a reply.
6. **Don't include secrets**: passwords, internal prices, private client details.
7. **Keep it up to date.** Wrong information here becomes wrong answers on your site.

## Example: what a good file looks like

`services.txt`:

```
Our Services

Acme Design offers three services:
1. Web design: custom websites for small businesses.
2. Branding: logos and brand guidelines.
3. Social media: monthly content and scheduling.

For pricing and timelines, please contact our team.
```

## After you add or change files

1. Save your files as plain text with UTF-8 encoding.
2. Run `python embed.py` to rebuild `index.json`.
3. Restart `python server.py`.

`python embed.py` stops with "No .txt files found" until you add at least one `.txt` file here.
