---
layout: post
title: "Automating Data Workflows with Pandas"
date: 2025-07-16
---

Let’s be honest: nobody gets into data engineering because they love doing the same thing over and over. That’s where pandas comes in clutch for automating the boring stuff. I’ve got a folder full of CSVs that land every morning, and pandas is my go-to for batch processing them before I’ve even had my coffee.

Here’s how I roll:

```python
import pandas as pd
import glob

for file in glob.glob('incoming/*.csv'):
    df = pd.read_csv(file)
    # Quick cleanup
    df = df.drop_duplicates()
    df['processed_at'] = pd.Timestamp.now()
    # Save to a new folder
    df.to_csv(f"processed/{file.split('/')[-1]}", index=False)
```

Set this up with a cron job or your favorite scheduler, and you’re basically on autopilot. Pandas isn’t just for notebooks—it’s a workhorse in production if you let it be.
