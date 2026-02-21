#!/bin/bash
echo "=== Checking GitHub Actions Deployment Status ==="
echo ""
echo "Recent commits:"
git log --oneline -5
echo ""
echo "GitHub Actions URL:"
echo "https://github.com/Aizekhan/youtube-content-automation/actions"
echo ""
echo "Latest navigation.js on production does NOT have Topics Queue link!"
echo "This means GitHub Actions is NOT deploying files!"
echo ""
echo "Files that need deployment:"
git diff --name-only origin/master~3 origin/master
