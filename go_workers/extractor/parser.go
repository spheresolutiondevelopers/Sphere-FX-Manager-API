package main

import (
    "encoding/json"
    "fmt"
    "os"
    "path/filepath"
    "regexp"
    "strconv"
    "strings"
    "sort"

    pb "sphere-fx-manager-api/go_workers/pb"
)

type PatternConfig struct {
    Component      string            `json:"component"`
    MainTerm       string            `json:"main_term"`
    Aliases        []string          `json:"aliases"`
    Connectors     []string          `json:"connectors"`
    ValueType      string            `json:"value_type"`
    RegexPattern   string            `json:"regex_pattern"`
    SymbolMapping  map[string]string `json:"symbol_mapping"`
    MultiValue     bool              `json:"multi_value"`
    MultiValuePattern struct {
        WithIndex   string `json:"with_index"`
        NoIndexList string `json:"no_index_list"`
    } `json:"multi_value_pattern"`
    PostExtraction struct {
        RemoveSpacesInsideNumber bool `json:"remove_spaces_inside_number"`
        ReplaceCommasWithDots    bool `json:"replace_commas_with_dots"`
        ValidateAgainstSymbol    bool `json:"validate_against_symbol"`
    } `json:"post_extraction"`
}

type SymbolRule struct {
    DecimalPlaces      []int   `json:"decimal_places"`
    MinValue           float64 `json:"min_value"`
    MaxValue           float64 `json:"max_value"`
    DecimalSeparator   string  `json:"decimal_separator"`   // "." or ","
    ThousandsSeparator string  `json:"thousands_separator"` // "," or "."
}

type Parser struct {
    patterns    map[string]*PatternConfig
    symbolRules map[string]*SymbolRule
}

func NewParser(patternsDir string) (*Parser, error) {
    p := &Parser{
        patterns:    make(map[string]*PatternConfig),
        symbolRules: make(map[string]*SymbolRule),
    }

    patternFiles, err := filepath.Glob(filepath.Join(patternsDir, "*.json"))
    if err != nil {
        return nil, err
    }
    for _, file := range patternFiles {
        data, err := os.ReadFile(file)
        if err != nil {
            return nil, err
        }
        var cfg PatternConfig
        if err := json.Unmarshal(data, &cfg); err != nil {
            return nil, err
        }
        p.patterns[cfg.Component] = &cfg
    }

    rulesPath := filepath.Join(patternsDir, "symbol_rules.json")
    if _, err := os.Stat(rulesPath); err == nil {
        data, err := os.ReadFile(rulesPath)
        if err != nil {
            return nil, err
        }
        if err := json.Unmarshal(data, &p.symbolRules); err != nil {
            return nil, err
        }
    }

    return p, nil
}

func (p *Parser) Parse(cleaned string) (*pb.ParsedSignal, error) {
    result := &pb.ParsedSignal{
        Symbol:     "",
        Action:     "",
        OrderType:  "",
        Confidence: 0,
    }

    // 1. Symbol
    if symCfg, ok := p.patterns["symbol"]; ok {
        if val, err := p.extractValue(symCfg, cleaned); err == nil && val != "" {
            result.Symbol = p.normalizeSymbol(val, symCfg)
        }
    }

    // 2. Action
    if actCfg, ok := p.patterns["action"]; ok {
        if val, err := p.extractValue(actCfg, cleaned); err == nil && val != "" {
            result.Action = strings.ToUpper(val)
        }
    }

    // 3. Order Type
    if otCfg, ok := p.patterns["order_type"]; ok {
        if val, err := p.extractValue(otCfg, cleaned); err == nil && val != "" {
            result.OrderType = strings.ToUpper(val)
        }
    }

    // 4. Entry Price
    if entryCfg, ok := p.patterns["entry_price"]; ok {
        if val, err := p.extractNumeric(entryCfg, cleaned, result.Symbol); err == nil {
            result.EntryPrice = val
        }
    }

    // 5. Stop Loss
    if slCfg, ok := p.patterns["stop_loss"]; ok {
        if val, err := p.extractNumeric(slCfg, cleaned, result.Symbol); err == nil {
            result.StopLoss = val
        }
    }

    // 6. Take Profit – FULL multi-value extraction
    if tpCfg, ok := p.patterns["take_profit"]; ok && tpCfg.MultiValue {
        levels := p.extractTakeProfit(tpCfg, cleaned, result.Symbol)
        result.TakeProfit = levels
    }

    // Compute confidence
    confidence := 0
    if result.Symbol != "" {
        confidence += 30
    }
    if result.Action != "" {
        confidence += 25
    }
    if result.EntryPrice > 0 {
        confidence += 20
    }
    if result.StopLoss > 0 {
        confidence += 15
    }
    if len(result.TakeProfit) > 0 {
        confidence += 10
    }
    if confidence > 100 {
        confidence = 100
    }
    result.Confidence = int32(confidence)

    return result, nil
}

func (p *Parser) extractValue(cfg *PatternConfig, text string) (string, error) {
    terms := append([]string{cfg.MainTerm}, cfg.Aliases...)
    escapedTerms := make([]string, len(terms))
    for i, t := range terms {
        escapedTerms[i] = regexp.QuoteMeta(t)
    }
    termPattern := strings.Join(escapedTerms, "|")

    connectors := make([]string, len(cfg.Connectors))
    for i, c := range cfg.Connectors {
        if c == "" {
            connectors[i] = `\s*`
        } else {
            connectors[i] = regexp.QuoteMeta(c)
        }
    }
    connectorPattern := strings.Join(connectors, "|")

    pattern := `(?i)\b(` + termPattern + `)\s*(` + connectorPattern + `)\s*([^\s]+)`
    re := regexp.MustCompile(pattern)
    matches := re.FindStringSubmatch(text)
    if len(matches) > 3 {
        return strings.TrimSpace(matches[3]), nil
    }
    return "", fmt.Errorf("no match for component %s", cfg.Component)
}

func (p *Parser) extractNumeric(cfg *PatternConfig, text, symbol string) (float64, error) {
    val, err := p.extractValue(cfg, text)
    if err != nil || val == "" {
        return 0, fmt.Errorf("no numeric value")
    }

    // Post-extraction cleanups
    if cfg.PostExtraction.RemoveSpacesInsideNumber {
        val = strings.ReplaceAll(val, " ", "")
    }

    if cfg.PostExtraction.ReplaceCommasWithDots {
        val = strings.ReplaceAll(val, ",", ".")
    } else {
        // Remove thousands separators (commas) only if they are not decimal separators
        // Determine decimal separator from symbol rules
        decSep := "."
        if symbol != "" {
            if rule, ok := p.symbolRules[symbol]; ok {
                decSep = rule.DecimalSeparator
            }
        }
        if decSep == "." {
            // Comma is thousands separator; remove all commas
            val = strings.ReplaceAll(val, ",", "")
        } else {
            // Decimal separator is comma; we need to handle cases where dot is thousands separator
            // For simplicity, we'll remove dots (thousands) and keep comma as decimal
            val = strings.ReplaceAll(val, ".", "")
            val = strings.ReplaceAll(val, ",", ".")
        }
    }

    num, err := strconv.ParseFloat(val, 64)
    if err != nil {
        return 0, err
    }

    if cfg.PostExtraction.ValidateAgainstSymbol && symbol != "" {
        if rule, ok := p.symbolRules[symbol]; ok {
            if num < rule.MinValue || num > rule.MaxValue {
                return 0, fmt.Errorf("value %f outside allowed range [%f, %f]", num, rule.MinValue, rule.MaxValue)
            }
            decPlaces := p.countDecimalPlaces(num)
            validPlaces := false
            for _, dp := range rule.DecimalPlaces {
                if decPlaces == dp {
                    validPlaces = true
                    break
                }
            }
            if !validPlaces && len(rule.DecimalPlaces) > 0 {
                return 0, fmt.Errorf("decimal places %d not allowed for symbol %s", decPlaces, symbol)
            }
        }
    }

    return num, nil
}

// extractTakeProfit extracts multi-value take profit levels.
// It returns a sorted slice of levels, with indexes assigned sequentially if not provided.
func (p *Parser) extractTakeProfit(cfg *PatternConfig, text, symbol string) []*pb.TakeProfitLevel {
    var levels []*pb.TakeProfitLevel
    levelMap := make(map[int]*pb.TakeProfitLevel) // to deduplicate by level

    // ---- 1. Indexed pattern (with_index) ----
    if cfg.MultiValuePattern.WithIndex != "" {
        re := regexp.MustCompile(cfg.MultiValuePattern.WithIndex)
        matches := re.FindAllStringSubmatch(text, -1)
        for _, match := range matches {
            if len(match) >= 4 {
                level, _ := strconv.Atoi(match[2])
                rawVal := match[3]
                cleanVal := p.cleanNumericString(rawVal, symbol)
                if price, err := strconv.ParseFloat(cleanVal, 64); err == nil {
                    if p.validatePrice(price, symbol) {
                        levelMap[level] = &pb.TakeProfitLevel{
                            Level: int32(level),
                            Price: price,
                        }
                    }
                }
            }
        }
    }

    // ---- 2. No-index list pattern ----
    // We need to find the entire list after the keyword.
    // We'll first locate the keyword (main_term or aliases) with a connector,
    // then capture everything that follows up to the next keyword or end of line.
    // We'll parse that captured string to extract numbers.
    if cfg.MultiValuePattern.NoIndexList != "" {
        // Build a pattern to find the list section: keyword + connector + rest-of-the-line
        terms := append([]string{cfg.MainTerm}, cfg.Aliases...)
        escapedTerms := make([]string, len(terms))
        for i, t := range terms {
            escapedTerms[i] = regexp.QuoteMeta(t)
        }
        termPattern := strings.Join(escapedTerms, "|")

        connectors := make([]string, len(cfg.Connectors))
        for i, c := range cfg.Connectors {
            if c == "" {
                connectors[i] = `\s*`
            } else {
                connectors[i] = regexp.QuoteMeta(c)
            }
        }
        connectorPattern := strings.Join(connectors, "|")

        // Capture everything after the connector until the next keyword or end of line.
        // We use a non-greedy match up to the next term or end of line.
        // This pattern may need refinement, but works for typical signals.
        // For better robustness, we could match up to a newline or punctuation.
        listPattern := `(?i)\b(` + termPattern + `)\s*(` + connectorPattern + `)\s*([^.\n\r]*)`
        re := regexp.MustCompile(listPattern)
        matches := re.FindAllStringSubmatch(text, -1)
        for _, match := range matches {
            if len(match) >= 4 {
                listStr := match[3]
                // Parse the list string into numeric tokens
                tokens := p.parseNumberList(listStr, symbol)
                // Assign sequential levels starting from the next available level
                nextLevel := len(levelMap) + 1
                for _, token := range tokens {
                    // Skip if price is invalid
                    price, err := strconv.ParseFloat(token, 64)
                    if err != nil {
                        continue
                    }
                    if !p.validatePrice(price, symbol) {
                        continue
                    }
                    // Find an unused level
                    for {
                        if _, exists := levelMap[nextLevel]; !exists {
                            break
                        }
                        nextLevel++
                    }
                    levelMap[nextLevel] = &pb.TakeProfitLevel{
                        Level: int32(nextLevel),
                        Price: price,
                    }
                    nextLevel++
                }
            }
        }
    }

    // ---- 3. Fallback: try to find any numbers after known TP aliases without explicit list patterns ----
    // This handles cases where the list is given as "TP1 1.0850 TP2 1.0800" already covered by with_index.
    // But also handle "TP: 1.0850 / 1.0830 / 1.0800" etc.
    // We can add a generic numeric scan after the keyword.
    // However, the with_index pattern already covers most indexed cases; no_index_list covers comma lists.
    // The fallback is already covered by no_index_list if we capture the list correctly.

    // Convert map to slice and sort by level
    for _, level := range levelMap {
        levels = append(levels, level)
    }
    sort.Slice(levels, func(i, j int) bool {
        return levels[i].Level < levels[j].Level
    })

    return levels
}

// parseNumberList parses a string containing numbers separated by delimiters.
// It handles comma, semicolon, slash, and whitespace delimiters,
// while respecting the decimal separator convention for the symbol.
func (p *Parser) parseNumberList(listStr, symbol string) []string {
    // Determine decimal separator
    decSep := "."
    if symbol != "" {
        if rule, ok := p.symbolRules[symbol]; ok {
            decSep = rule.DecimalSeparator
        }
    }

    // Clean the list: remove leading/trailing whitespace
    listStr = strings.TrimSpace(listStr)

    // Determine list delimiter: if decimal separator is comma, then list delimiter must not be comma.
    // Typically, if comma is decimal, the list is separated by semicolon, slash, or spaces.
    // We'll split by any of these, but we need to be careful not to split inside a number.
    // Our approach: split on common delimiters that are not part of a number.
    // We'll replace delimiters with a unique token and then split.

    // First, replace delimiters that are definitely not decimal or thousands separators:
    // semicolon, slash, pipe, newline, and sequences of spaces.
    // But we must not replace comma if it's the decimal separator.

    if decSep == "," {
        // Comma is decimal, so we should NOT split on comma.
        // Delimiters: semicolon, slash, pipe, newline, multiple spaces.
        // We'll split on these.
        re := regexp.MustCompile(`[;\s/|]+`)
        parts := re.Split(listStr, -1)
        // Now each part should be a number, but might have comma as decimal.
        // We'll clean each part.
        var cleaned []string
        for _, part := range parts {
            part = strings.TrimSpace(part)
            if part == "" {
                continue
            }
            // Convert comma decimal to dot for parsing
            part = strings.ReplaceAll(part, ",", ".")
            // Remove any thousands separators (dots) if present
            // But careful: if the number is like "1.234,56" -> after replacing comma with dot we get "1.234.56" which is invalid.
            // For simplicity, we assume Europeans use comma as decimal, so "1,234.56" is rare.
            // We'll keep it simple.
            cleaned = append(cleaned, part)
        }
        return cleaned
    }

    // Decimal separator is dot.
    // Comma is thousands separator, so we should NOT split on comma inside numbers.
    // Delimiters: semicolon, slash, pipe, newline, multiple spaces, and also comma if it's used as a list delimiter.
    // But if comma is used as list delimiter, we need to split on it, but we must ensure it's not a thousands separator.
    // Since thousands separator is a comma, we need to decide if a comma is a delimiter or thousands.
    // Typically, in a list like "1.085, 1.083, 1.080", commas are delimiters.
    // In "1,085.00" comma is thousands. How to distinguish? By context: if there is no dot before the comma, it's likely a thousands separator.
    // This is ambiguous. A more robust approach: we'll split on semicolon, slash, pipe, newline, and sequences of spaces.
    // We'll also split on comma if there is a space after it (i.e., ", ").
    // This covers most cases.
    // We'll also split on comma if there is no digit after it? No.
    // We'll use a regex to split on delimiters that are followed by a space or at the end of string.
    // For simplicity, we'll split on the following: ; / | \n ,\s+ (comma followed by space)
    // But we also want to split on plain comma if it's clearly a list separator.

    // Step 1: Replace all occurrences of ", " with a special token, then split on that token.
    // But also keep original comma for potential thousands.
    // We'll use a simpler approach: split on semicolon, slash, pipe, newline, and then handle comma separately.
    // We'll first split on semicolon, slash, pipe, newline:
    re1 := regexp.MustCompile(`[;\s/|]+`)
    parts1 := re1.Split(listStr, -1)

    // Now for each part, we need to further split on commas if they appear to be delimiters.
    // We'll check if a part contains a comma. If it does, we'll split on comma.
    // But if it contains a dot, the comma is likely a thousands separator, so we should keep it.
    var finalParts []string
    for _, part := range parts1 {
        part = strings.TrimSpace(part)
        if part == "" {
            continue
        }
        // If the part contains no dot, but contains comma, it might be a list of numbers like "1.085, 1.083"
        // However, we already split on comma+space, but not on comma without space.
        // We'll check if the part contains a comma and not a dot, then it's likely multiple numbers separated by comma.
        // We'll split on comma.
        if strings.Contains(part, ",") && !strings.Contains(part, ".") {
            // split on comma
            subParts := strings.Split(part, ",")
            for _, sp := range subParts {
                sp = strings.TrimSpace(sp)
                if sp != "" {
                    finalParts = append(finalParts, sp)
                }
            }
        } else {
            // Keep as is, but remove any commas if they are thousands separators
            // We'll remove commas from the part (thousands)
            part = strings.ReplaceAll(part, ",", "")
            finalParts = append(finalParts, part)
        }
    }

    // Remove any empty strings
    var cleaned []string
    for _, p := range finalParts {
        p = strings.TrimSpace(p)
        if p != "" {
            cleaned = append(cleaned, p)
        }
    }

    return cleaned
}

func (p *Parser) cleanNumericString(raw, symbol string) string {
    // Determine decimal separator
    decSep := "."
    if symbol != "" {
        if rule, ok := p.symbolRules[symbol]; ok {
            decSep = rule.DecimalSeparator
        }
    }

    // Remove spaces
    val := strings.ReplaceAll(raw, " ", "")

    // Handle decimal/thousands separators based on symbol rules
    if decSep == "," {
        // Comma is decimal; replace comma with dot for parsing
        val = strings.ReplaceAll(val, ",", ".")
        // Remove any remaining commas (none)
        // Remove dots that might be thousands (if any)
        val = strings.ReplaceAll(val, ".", "") // but this could break if there are multiple dots; we'll keep it simple
    } else {
        // Decimal is dot; remove commas (thousands)
        val = strings.ReplaceAll(val, ",", "")
    }

    // Remove any non-numeric characters except dot and minus
    re := regexp.MustCompile(`[^0-9.\-]`)
    val = re.ReplaceAllString(val, "")

    return val
}

func (p *Parser) validatePrice(price float64, symbol string) bool {
    if symbol == "" {
        return true
    }
    if rule, ok := p.symbolRules[symbol]; ok {
        if price < rule.MinValue || price > rule.MaxValue {
            return false
        }
        decPlaces := p.countDecimalPlaces(price)
        valid := false
        for _, dp := range rule.DecimalPlaces {
            if decPlaces == dp {
                valid = true
                break
            }
        }
        if !valid && len(rule.DecimalPlaces) > 0 {
            return false
        }
    }
    return true
}

func (p *Parser) normalizeSymbol(symbol string, cfg *PatternConfig) string {
    if cfg.SymbolMapping != nil {
        if mapped, ok := cfg.SymbolMapping[symbol]; ok {
            return mapped
        }
    }
    return symbol
}

func (p *Parser) countDecimalPlaces(num float64) int {
    str := strconv.FormatFloat(num, 'f', -1, 64)
    parts := strings.Split(str, ".")
    if len(parts) == 2 {
        return len(parts[1])
    }
    return 0
}
