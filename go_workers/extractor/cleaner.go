package main

import (
    "encoding/json"
    "os"
    "path/filepath"
    "regexp"
    "strings"
    "unicode"
)

type Cleaner struct {
    fancyMap     map[rune]rune
    emojiRegex   *regexp.Regexp
    markupRegex  *regexp.Regexp
    htmlTagRegex *regexp.Regexp
    whitespaceRx *regexp.Regexp
    connectorSet map[rune]bool
}

// NewCleaner initializes the cleaner with a fancy character map.
func NewCleaner(configDir string) (*Cleaner, error) {
    // Load fancy_char_map.json
    mapPath := filepath.Join(configDir, "fancy_char_map.json")
    data, err := os.ReadFile(mapPath)
    if err != nil {
        return nil, err
    }
    var rawMap map[string]string
    if err := json.Unmarshal(data, &rawMap); err != nil {
        return nil, err
    }

    fancyMap := make(map[rune]rune)
    for k, v := range rawMap {
        // Convert string keys (UTF-8) to runes
        kr := []rune(k)
        vr := []rune(v)
        if len(kr) == 1 && len(vr) == 1 {
            fancyMap[kr[0]] = vr[0]
        }
    }

    // Emoji regex (simplified; in production use a comprehensive set)
    // Using Unicode block ranges for common emoji
    emojiPattern := `[\x{1F300}-\x{1F5FF}\x{1F600}-\x{1F64F}\x{1F680}-\x{1F6FF}\x{1F700}-\x{1F77F}\x{1F780}-\x{1F7FF}\x{1F800}-\x{1F8FF}\x{1F900}-\x{1F9FF}\x{1FA00}-\x{1FA6F}\x{1FA70}-\x{1FAFF}\x{2600}-\x{26FF}\x{2700}-\x{27BF}]`
    emojiRx := regexp.MustCompile(emojiPattern)

    // Markdown/Telegram formatting: **bold**, __italic__, `monospace`, [text](url)
    markupRx := regexp.MustCompile(`\*\*.*?\*\*|__.*?__|` + "`" + `.*?` + "`" + `|\[.*?\]\(.*?\)`)

    // HTML tags: <b>, <i>, <u>, <a>, etc.
    htmlTagRx := regexp.MustCompile(`<[^>]*>`)

    // Whitespace collapse
    whitespaceRx := regexp.MustCompile(`\s+`)

    // Connector punctuation to preserve
    connectorSet := map[rune]bool{
        ':': true, ';': true, '-': true, '–': true,
        '#': true, '=': true, '|': true, '/': true,
    }

    return &Cleaner{
        fancyMap:     fancyMap,
        emojiRegex:   emojiRx,
        markupRegex:  markupRx,
        htmlTagRegex: htmlTagRx,
        whitespaceRx: whitespaceRx,
        connectorSet: connectorSet,
    }, nil
}

// Clean applies the full cleaning pipeline to raw text.
func (c *Cleaner) Clean(raw string) string {
    // 1. Remove emojis
    text := c.emojiRegex.ReplaceAllString(raw, "")

    // 2. Remove Telegram/Markdown formatting
    text = c.markupRegex.ReplaceAllString(text, "")

    // 3. Remove HTML tags
    text = c.htmlTagRegex.ReplaceAllString(text, "")

    // 4. Replace HTML entities (common ones)
    text = c.replaceHTMLEntities(text)

    // 5. Normalize fancy Unicode to ASCII using the map
    text = c.normalizeFancy(text)

    // 6. Collapse whitespace (multiple spaces/newlines -> single space)
    text = c.whitespaceRx.ReplaceAllString(text, " ")
    text = strings.TrimSpace(text)

    // 7. Preserve connector punctuation: we don't remove them,
    // but we ensure they are not stripped by any other step.
    // Already kept since we only remove emoji, markup, and collapse whitespace.

    return text
}

// normalizeFancy replaces each fancy Unicode character with its ASCII equivalent.
func (c *Cleaner) normalizeFancy(text string) string {
    var b strings.Builder
    b.Grow(len(text))
    for _, r := range text {
        if mapped, ok := c.fancyMap[r]; ok {
            b.WriteRune(mapped)
        } else {
            b.WriteRune(r)
        }
    }
    return b.String()
}

// replaceHTMLEntities decodes common HTML entities.
func (c *Cleaner) replaceHTMLEntities(text string) string {
    replacer := strings.NewReplacer(
        "&amp;", "&",
        "&lt;", "<",
        "&gt;", ">",
        "&quot;", "\"",
        "&apos;", "'",
        "&nbsp;", " ",
        "&mdash;", "—",
        "&ndash;", "–",
        "&bull;", "•",
        "&copy;", "©",
        "&reg;", "®",
        "&trade;", "™",
        "&euro;", "€",
        "&pound;", "£",
        "&yen;", "¥",
        "&cent;", "¢",
        "&sect;", "§",
        "&deg;", "°",
        "&plusmn;", "±",
        "&frac12;", "½",
        "&frac14;", "¼",
        "&frac34;", "¾",
    )
    return replacer.Replace(text)
}
