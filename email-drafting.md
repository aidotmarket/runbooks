# Email Drafting

## What it does

Prepares outreach and follow-up emails as HTML files with pre-filled `mailto:` links. Gmail adds Max's signature automatically.

## How it works

```
Vulcan drafts email using write-like-max voice skill
  → Saves as HTML file to ~/Downloads/
  → HTML contains mailto: link with pre-filled to, subject, body
  → Max clicks link → opens Gmail compose
  → Gmail auto-adds signature
  → Max reviews and sends
```

## Voice rules (write-like-max)

- Short to medium sentences, active voice
- Plain words: "got", "doing", "stuff", "cool"
- NEVER: em-dashes, semicolons, "delve", "leverage", "robust", "comprehensive"
- Greeting: "Hi [name]," (never "Dear")
- Close: "Best, Max" (not "Best regards")
- Under 250 words for outreach, under 150 for follow-ups
- No bullet points in emails

## File location

Always save to `/Users/max/Downloads/`, not Desktop.

## CRM integration

After drafting, log the outreach in CRM:
```
crm_log_interaction(entity_id, interaction_type="email", content="...", summary="...")
```
