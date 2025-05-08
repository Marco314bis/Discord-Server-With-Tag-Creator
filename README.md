# Discord Server With Tag Creator

## WARNING: Since May 8, 2025, at 7:00 PM UTC, Discord has removed the ability for new servers to access tags, due to people generating them. Therefore, the program will not find any new servers. So don't waste time by running it.

A simple python program used to automatically create servers with tags, using multiple accounts simultaneously.

You’ll need to install the `curl_cffi` module:

```bash
pip install curl_cffi
```

The code does not handle potential errors like rate limits because I didn’t need that and didn't care, and I made it very quickly (just over 30 minutes).  
I wrote this program when only 1 in 1,000 servers had the experiment available, so it was still highly wanted.  
I was able to get around 10 servers with the feature per hour using 15 accounts simultaneously.  
Do not use accounts with MFA enabled, as they won’t be able to delete the servers.  
I imagine there’s a potential risk of getting banned, so be careful :p

If you prefer using a script to run directly in the console, you can use [bytexenon's script](https://gist.github.com/bytexenon/db8e7dce72bb6a21aa2277de834de1d1).

If you don’t know how to run a python program, just don’t run it.  
If you want better error handling, go ahead and add it yourself.
