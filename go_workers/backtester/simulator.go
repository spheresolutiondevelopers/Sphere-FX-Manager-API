package main

import (
    "fmt"
    "math"
    "sort"
    "sync"
    "time"

    "google.golang.org/protobuf/types/known/timestamppb"
)

type Signal struct {
    ID          int64
    Symbol      string
    Action      string
    OrderType   string
    EntryPrice  float64
    StopLoss    float64
    TakeProfit  []float64
    Timestamp   time.Time
    Source      string
    Confidence  int
}

type Trade struct {
    SignalID   int64
    Symbol     string
    Action     string
    EntryPrice float64
    ExitPrice  float64
    RRAchieved float64
    Outcome    string // TP_HIT, SL_HIT, OPEN, CANCELLED
}

type LogLine struct {
    Message  string
    Level    string
    Progress int
}

type SimulationResult struct {
    RunID         int64
    TotalSignals  int
    WinCount      int
    LossCount     int
    WinRate       float64
    TotalRR       float64
    ProfitFactor  float64
    MaxDrawdown   float64
    SharpeRatio   float64
    EquityCurve   []float64
    Trades        []Trade
    Logs          []LogLine
    StartedAt     time.Time
    FinishedAt    time.Time
}

type Simulator struct {
    cfg       *Config
    mu        sync.RWMutex
    cache     map[int64]SimulationResult
    runCounter int64
    resultTTL time.Duration
}

func NewSimulator(cfg *Config) *Simulator {
    return &Simulator{
        cfg:       cfg,
        cache:     make(map[int64]SimulationResult),
        runCounter: 0,
        resultTTL: time.Duration(cfg.CacheTTLSeconds) * time.Second,
    }
}

func (s *Simulator) Run(signals []Signal) SimulationResult {
    s.mu.Lock()
    s.runCounter++
    runID := s.runCounter
    s.mu.Unlock()

    startedAt := time.Now()
    logs := []LogLine{
        {Message: fmt.Sprintf("Starting backtest run #%d with %d signals", runID, len(signals)), Level: "INFO", Progress: 0},
        {Message: fmt.Sprintf("RR: %.2f, Spread: %.2f pips, TP Strategy: %s", s.cfg.DefaultRR, s.cfg.SpreadPips, s.cfg.DefaultTPStrategy), Level: "INFO", Progress: 0},
    }

    // Sort by timestamp
    sorted := make([]Signal, len(signals))
    copy(sorted, signals)
    sort.Slice(sorted, func(i, j int) bool {
        return sorted[i].Timestamp.Before(sorted[j].Timestamp)
    })

    var trades []Trade
    var equityPoints []float64
    cumRR := 0.0
    wins, losses := 0, 0

    for i, sig := range sorted {
        trade := s.simulateTrade(sig)
        trades = append(trades, trade)

        if trade.Outcome == "TP_HIT" {
            wins++
            cumRR += trade.RRAchieved
        } else if trade.Outcome == "SL_HIT" {
            losses++
            cumRR += trade.RRAchieved // negative
        }
        equityPoints = append(equityPoints, cumRR)

        if (i+1)%10 == 0 || i == len(sorted)-1 {
            progress := int(float64(i+1) / float64(len(sorted)) * 100)
            logs = append(logs, LogLine{
                Message:  fmt.Sprintf("Processed %d/%d signals ... RR: %.2f", i+1, len(sorted), cumRR),
                Level:    "INFO",
                Progress: progress,
            })
        }
    }

    totalSignals := len(trades)
    winRate := float64(wins) / float64(totalSignals) * 100
    totalRR := cumRR
    profitFactor := calculateProfitFactor(trades)
    maxDrawdown := calculateMaxDrawdown(equityPoints)
    sharpeRatio := calculateSharpeRatio(equityPoints)

    finishedAt := time.Now()
    logs = append(logs, LogLine{
        Message:  fmt.Sprintf("Backtest done in %.2fs. Win Rate: %.2f%%, Total RR: %.2f", finishedAt.Sub(startedAt).Seconds(), winRate, totalRR),
        Level:    "INFO",
        Progress: 100,
    })

    result := SimulationResult{
        RunID:         runID,
        TotalSignals:  totalSignals,
        WinCount:      wins,
        LossCount:     losses,
        WinRate:       winRate,
        TotalRR:       totalRR,
        ProfitFactor:  profitFactor,
        MaxDrawdown:   maxDrawdown,
        SharpeRatio:   sharpeRatio,
        EquityCurve:   equityPoints,
        Trades:        trades,
        Logs:          logs,
        StartedAt:     startedAt,
        FinishedAt:    finishedAt,
    }

    s.mu.Lock()
    s.cache[runID] = result
    s.mu.Unlock()

    return result
}

func (s *Simulator) simulateTrade(sig Signal) Trade {
    entry := sig.EntryPrice
    // Apply spread (approximate)
    spreadAdj := s.cfg.SpreadPips / 10000.0
    if sig.Action == "BUY" {
        entry += spreadAdj
    } else {
        entry -= spreadAdj
    }

    exitPrice := entry
    outcome := "OPEN"
    rr := 0.0

    if sig.Action == "BUY" {
        // TP above entry, SL below
        if len(sig.TakeProfit) > 0 {
            tpPrice := sig.TakeProfit[0]
            if tpPrice > entry {
                exitPrice = tpPrice
                outcome = "TP_HIT"
                rr = (tpPrice - entry) / (entry - sig.StopLoss)
            } else if sig.StopLoss < entry {
                exitPrice = sig.StopLoss
                outcome = "SL_HIT"
                rr = (sig.StopLoss - entry) / (entry - sig.StopLoss)
                if rr > 0 {
                    rr = -rr
                }
            }
        } else {
            if sig.StopLoss < entry {
                exitPrice = sig.StopLoss
                outcome = "SL_HIT"
                rr = (sig.StopLoss - entry) / (entry - sig.StopLoss)
                if rr > 0 {
                    rr = -rr
                }
            }
        }
    } else { // SELL
        if len(sig.TakeProfit) > 0 {
            tpPrice := sig.TakeProfit[0]
            if tpPrice < entry {
                exitPrice = tpPrice
                outcome = "TP_HIT"
                rr = (entry - tpPrice) / (entry - sig.StopLoss)
            } else if sig.StopLoss > entry {
                exitPrice = sig.StopLoss
                outcome = "SL_HIT"
                rr = (entry - sig.StopLoss) / (entry - sig.StopLoss)
                if rr > 0 {
                    rr = -rr
                }
            }
        } else {
            if sig.StopLoss > entry {
                exitPrice = sig.StopLoss
                outcome = "SL_HIT"
                rr = (entry - sig.StopLoss) / (entry - sig.StopLoss)
                if rr > 0 {
                    rr = -rr
                }
            }
        }
    }

    // Scale RR by default factor
    rr = rr * s.cfg.DefaultRR / 2.0

    return Trade{
        SignalID:   sig.ID,
        Symbol:     sig.Symbol,
        Action:     sig.Action,
        EntryPrice: entry,
        ExitPrice:  exitPrice,
        RRAchieved: rr,
        Outcome:    outcome,
    }
}

func (s *Simulator) GetCachedResult(runID int64) (SimulationResult, bool) {
    s.mu.RLock()
    defer s.mu.RUnlock()
    res, ok := s.cache[runID]
    return res, ok
}

// --- Metric functions (in same file to avoid separate package) ---

func calculateProfitFactor(trades []Trade) float64 {
    grossProfit := 0.0
    grossLoss := 0.0
    for _, t := range trades {
        if t.RRAchieved > 0 {
            grossProfit += t.RRAchieved
        } else {
            grossLoss += math.Abs(t.RRAchieved)
        }
    }
    if grossLoss == 0 {
        return math.Inf(1)
    }
    return grossProfit / grossLoss
}

func calculateMaxDrawdown(equity []float64) float64 {
    if len(equity) < 2 {
        return 0
    }
    maxDD := 0.0
    peak := equity[0]
    for _, v := range equity {
        if v > peak {
            peak = v
        }
        dd := peak - v
        if dd > maxDD {
            maxDD = dd
        }
    }
    return maxDD
}

func calculateSharpeRatio(equity []float64) float64 {
    if len(equity) < 2 {
        return 0
    }
    returns := make([]float64, len(equity)-1)
    for i := 0; i < len(equity)-1; i++ {
        returns[i] = equity[i+1] - equity[i]
    }
    mean := 0.0
    for _, r := range returns {
        mean += r
    }
    mean /= float64(len(returns))
    var variance float64
    for _, r := range returns {
        variance += (r - mean) * (r - mean)
    }
    variance /= float64(len(returns))
    stdDev := math.Sqrt(variance)
    if stdDev == 0 {
        return 0
    }
    return mean / stdDev
}