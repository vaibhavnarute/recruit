# 📊 Logging Quick Reference

## View Logs

```bash
# Real-time logs (all)
tail -f backend/logs/ai_recruiter_*.log

# TTS logs only
tail -f backend/logs/tts_*.log

# Bot logs only
tail -f backend/logs/meeting_bot_*.log

# Errors only
tail -f backend/logs/errors_*.log
```

## Search Logs

```bash
# Find all TTS generations today
grep "TTS GENERATION SUCCESSFUL" backend/logs/tts_$(date +%Y%m%d).log

# Find all bot joins today
grep "BOT JOINED MEETING" backend/logs/meeting_bot_$(date +%Y%m%d).log

# Find all errors today
grep "ERROR" backend/logs/errors_$(date +%Y%m%d).log

# Count TTS requests
grep "TTS SPEAK REQUEST" backend/logs/tts_*.log | wc -l
```

## Log Emojis

- 🎬 START
- ✅ SUCCESS
- ❌ ERROR
- 🔊 TTS
- 🤖 BOT
- 🎤 INTERVIEW
- 💾 DATABASE
- 🔌 API

## Log Files Location

`backend/logs/ai_recruiter_YYYYMMDD.log` - All logs  
`backend/logs/tts_YYYYMMDD.log` - TTS only  
`backend/logs/meeting_bot_YYYYMMDD.log` - Bot only  
`backend/logs/errors_YYYYMMDD.log` - Errors only

## Cleanup

```bash
# Delete logs older than 30 days
find backend/logs/ -name "*.log" -mtime +30 -delete
```
