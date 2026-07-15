#!/bin/bash
sqlite3 /opt/zinaida/smm_factory.db "DELETE FROM task_checkpoints WHERE created_at < datetime('now', '-7 days');"
