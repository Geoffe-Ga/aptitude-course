#!/bin/bash

# Unzip all files in google_docs
cd google_docs
for zipfile in *.zip; do
    [ -e "$zipfile" ] || continue
    unzip -o "$zipfile"
done

# Convert all HTML files to markdown
for htmlfile in *.html; do
    [ -e "$htmlfile" ] || continue
    filename=$(basename "$htmlfile" .html)
    pandoc "$htmlfile" -f html -t gfm -o "../markdown/${filename}.md" --extract-media=../markdown/images
    echo "Converted: $filename"
done

cd ..
echo "Done! Markdown files are in ./markdown/"
