package simulator

import (
    "fmt"
    "math"
    "sort"
    "sync"
    "time"

    "sphere-fx-manager-api/go_workers/backtester/config"
    "sphere-fx-manager-api/go_workers/backtester/metrics"
    "sphere-fx-manager-api/go_workers/backtester/risk"
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
    SignalID    int64
    Symbol      string
    Action      string
    EntryPrice  float64
    ExitPrice   float64
    RRAchieved  float64
    Outcome     string // TP_HIT, SL_HIT, OPEN, CANCELLED
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
    cfg            *config.Config
    mu             sync.RWMutex
    cache          map[int64]SimulationResult
    runCounter     int64
    resultTTL      time.Duration
}

func NewSimulator(cfg *config.Config) *Simulator {
    return &Simulator{
        cfg:         cfg,
        cache:       make(map[int64]SimulationResult),
        runCounter:  0,
        resultTTL:   time.Duration(cfg.CacheTTLSeconds) * time.Second,
    }
}

func (s *Simulator) Config() *config.Config {
    return s.cfg
}

func (s *Simulator) Run(signals []Signal) SimulationResult {
    s.mu.Lock()
    s.runCounter++
    runID := s.runCounter
    s.mu.Unlock()

    startedAt := time.Now()
    logs := []LogLine{
        {Message: fmt.Sprintf("Starting backtest run #%d with %d signals", runID, len(signals)), Level: "INFO", Progress: 0},
        {Message: fmt.Sprintf("RR ratio: %.2f, Spread: %.2f pips, TP Strategy: %s", s.cfg.DefaultRR, s.cfg.SpreadPips, s.cfg.DefaultTPStrategy), Level: "INFO", Progress: 0},
    }

    // Sort signals by timestamp
    sortedSignals := make([]Signal, len(signals))
    copy(sortedSignals, signals)
    sort.Slice(sortedSignals, func(i, j int) bool {
        return sortedSignals[i].Timestamp.Before(sortedSignals[j].Timestamp)
    })

    // Simulate each signal
    var trades []Trade
    var equityPoints []float64
    cumulativeRR := 0.0
    wins := 0
    losses := 0

    for i, sig := range sortedSignals {
        // Simulate trade
        trade := s.simulateTrade(sig)
        trades = append(trades, trade)

        if trade.Outcome == "TP_HIT" {
            wins++
            cumulativeRR += trade.RRAchieved
        } else if trade.Outcome == "SL_HIT" {
            losses++
            cumulativeRR += trade.RRAchieved // negative RR
        } else {
            // OPEN or CANCELLED - treat as 0 RR
        }

        equityPoints = append(equityPoints, cumulativeRR)

        // Log progress
        if (i+1)%10 == 0 || i == len(sortedSignals)-1 {
            progress := int(float64(i+1) / float64(len(sortedSignals)) * 100)
            logs = append(logs, LogLine{
                Message:  fmt.Sprintf("Processed %d/%d signals... (RR: %.2f)", i+1, len(sortedSignals), cumulativeRR),
                Level:    "INFO",
                Progress: progress,
            })
        }
    }

    // Compute metrics
    totalSignals := len(trades)
    winCount := wins
    lossCount := losses
    winRate := float64(winCount) / float64(totalSignals) * 100
    totalRR := cumulativeRR
    profitFactor := metrics.CalculateProfitFactor(trades)
    maxDrawdown := metrics.CalculateMaxDrawdown(equityPoints)
    sharpeRatio := metrics.CalculateSharpeRatio(equityPoints)

    // Log completion
    finishedAt := time.Now()
    duration := finishedAt.Sub(startedAt)
    logs = append(logs, LogLine{
        Message:  fmt.Sprintf("Backtest completed in %.2f seconds. Win Rate: %.2f%%, Total RR: %.2f", duration.Seconds(), winRate, totalRR),
        Level:    "INFO",
        Progress: 100,
    })

    result := SimulationResult{
        RunID:         runID,
        TotalSignals:  totalSignals,
        WinCount:      winCount,
        LossCount:     lossCount,
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

    // Cache result
    s.mu.Lock()
    s.cache[runID] = result
    s.mu.Unlock()

    return result
}

func (s *Simulator) simulateTrade(sig Signal) Trade {
    // Apply spread to entry price
    entryPrice := sig.EntryPrice
    spreadAdjustment := s.cfg.SpreadPips / 10000.0 // approximate pips to price
    if sig.Action == "BUY" {
        entryPrice += spreadAdjustment
    } else {
        entryPrice -= spreadAdjustment
    }

    // Determine exit price based on TP/SL
    exitPrice := entryPrice
    outcome := "OPEN"
    rr := 0.0

    if sig.Action == "BUY" {
        // BUY: TP is above entry, SL is below
        // Check if SL or TP hit first
        // We assume a simple model: if TP is reached before SL
        if len(sig.TakeProfit) > 0 {
            // Sequential TP: take first TP
            tpPrice := sig.TakeProfit[0]
            if tpPrice > entryPrice {
                exitPrice = tpPrice
                outcome = "TP_HIT"
                rr = (tpPrice - entryPrice) / (entryPrice - sig.StopLoss)
            } else if sig.StopLoss < entryPrice {
                exitPrice = sig.StopLoss
                outcome = "SL_HIT"
                rr = (sig.StopLoss - entryPrice) / (entryPrice - sig.StopLoss)
                if rr > 0 {
                    rr = -rr // negative for loss
                }
            }
        } else {
            // No TP: check SL only
            if sig.StopLoss < entryPrice {
                exitPrice = sig.StopLoss
                outcome = "SL_HIT"
                rr = (sig.StopLoss - entryPrice) / (entryPrice - sig.StopLoss)
                if rr > 0 {
                    rr = -rr
                }
            }
        }
    } else { // SELL
        // SELL: TP is below entry, SL is above
        if len(sig.TakeProfit) > 0 {
            tpPrice := sig.TakeProfit[0]
            if tpPrice < entryPrice {
                exitPrice = tpPrice
                outcome = "TP_HIT"
                rr = (entryPrice - tpPrice) / (entryPrice - sig.StopLoss)
            } else if sig.StopLoss > entryPrice {
                exitPrice = sig.StopLoss
                outcome = "SL_HIT"
                rr = (entryPrice - sig.StopLoss) / (entryPrice - sig.StopLoss)
                if rr > 0 {
                    rr = -rr
                }
            }
        } else {
            if sig.StopLoss > entryPrice {
                exitPrice = sig.StopLoss
                outcome = "SL_HIT"
                rr = (entryPrice - sig.StopLoss) / (entryPrice - sig.StopLoss)
                if rr > 0 {
                    rr = -rr
                }
            }
        }
    }

    // Apply RR multiplier from config
    rr = rr * s.cfg.DefaultRR / 2.0 // normalize

    return Trade{
        SignalID:   sig.ID,
        Symbol:     sig.Symbol,
        Action:     sig.Action,
        EntryPrice: entryPrice,
        ExitPrice:  exitPrice,
        RRAchieved: rr,
        Outcome:    outcome,
    }
}

func (s *Simulator) GetCachedResult(runID int64) (SimulationResult, bool) {
    s.mu.RLock()
    defer s.mu.RUnlock()
    result, ok := s.cache[runID]
    return result, ok
}