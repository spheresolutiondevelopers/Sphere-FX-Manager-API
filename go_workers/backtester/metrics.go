package main

import (
    "math"
    //"sort"
)

func CalculateProfitFactor(trades []Trade) float64 {
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

func CalculateMaxDrawdown(equityCurve []float64) float64 {
    if len(equityCurve) < 2 {
        return 0
    }
    maxDrawdown := 0.0
    peak := equityCurve[0]
    for _, val := range equityCurve {
        if val > peak {
            peak = val
        }
        drawdown := peak - val
        if drawdown > maxDrawdown {
            maxDrawdown = drawdown
        }
    }
    return maxDrawdown
}

func CalculateSharpeRatio(equityCurve []float64) float64 {
    if len(equityCurve) < 2 {
        return 0
    }
    // Calculate returns from equity curve
    returns := make([]float64, len(equityCurve)-1)
    for i := 0; i < len(equityCurve)-1; i++ {
        returns[i] = equityCurve[i+1] - equityCurve[i]
    }
    // Mean return
    mean := 0.0
    for _, r := range returns {
        mean += r
    }
    mean /= float64(len(returns))

    // Standard deviation
    variance := 0.0
    for _, r := range returns {
        variance += (r - mean) * (r - mean)
    }
    variance /= float64(len(returns))
    stdDev := math.Sqrt(variance)

    if stdDev == 0 {
        return 0
    }
    // Sharpe ratio = mean / stdDev (simplified, no risk-free rate)
    return mean / stdDev
}

func CalculateWinRate(trades []Trade) float64 {
    if len(trades) == 0 {
        return 0
    }
    wins := 0
    for _, t := range trades {
        if t.RRAchieved > 0 {
            wins++
        }
    }
    return float64(wins) / float64(len(trades)) * 100
}

func CalculateAverageRR(trades []Trade) float64 {
    if len(trades) == 0 {
        return 0
    }
    total := 0.0
    for _, t := range trades {
        total += t.RRAchieved
    }
    return total / float64(len(trades))
}

func CalculateConsecutiveWins(trades []Trade) int {
    maxStreak := 0
    currentStreak := 0
    for _, t := range trades {
        if t.RRAchieved > 0 {
            currentStreak++
            if currentStreak > maxStreak {
                maxStreak = currentStreak
            }
        } else {
            currentStreak = 0
        }
    }
    return maxStreak
}

func CalculateConsecutiveLosses(trades []Trade) int {
    maxStreak := 0
    currentStreak := 0
    for _, t := range trades {
        if t.RRAchieved <= 0 {
            currentStreak++
            if currentStreak > maxStreak {
                maxStreak = currentStreak
            }
        } else {
            currentStreak = 0
        }
    }
    return maxStreak
}
