package risk

import (
    "math"
    "sort"
)

func CalculateKellyFraction(winRate float64, avgWin float64, avgLoss float64) float64 {
    if avgLoss == 0 {
        return 0
    }
    // Kelly = (winRate * avgWin - (1 - winRate) * avgLoss) / avgWin
    // Simplified Kelly for trading
    profitFactor := (winRate * avgWin) / ((1 - winRate) * avgLoss)
    if profitFactor <= 0 {
        return 0
    }
    kelly := (winRate - (1-winRate)/profitFactor) / profitFactor
    if kelly < 0 {
        return 0
    }
    return kelly
}

func CalculateSortinoRatio(returns []float64, targetReturn float64) float64 {
    if len(returns) < 2 {
        return 0
    }
    // Mean return
    mean := 0.0
    for _, r := range returns {
        mean += r
    }
    mean /= float64(len(returns))

    // Downside deviation (only negative returns below target)
    downsideVariance := 0.0
    count := 0
    for _, r := range returns {
        if r < targetReturn {
            downsideVariance += (r - targetReturn) * (r - targetReturn)
            count++
        }
    }
    if count == 0 {
        return 0
    }
    downsideStdDev := math.Sqrt(downsideVariance / float64(count))
    if downsideStdDev == 0 {
        return 0
    }
    return (mean - targetReturn) / downsideStdDev
}

func CalculateCalmarRatio(totalRR float64, maxDrawdown float64) float64 {
    if maxDrawdown == 0 {
        return math.Inf(1)
    }
    return totalRR / maxDrawdown
}

func CalculateVaR(returns []float64, confidenceLevel float64) float64 {
    if len(returns) < 2 {
        return 0
    }
    sorted := make([]float64, len(returns))
    copy(sorted, returns)
    sort.Float64s(sorted)
    // 1 - confidenceLevel percentile
    index := int(float64(len(sorted)) * (1 - confidenceLevel))
    if index >= len(sorted) {
        index = len(sorted) - 1
    }
    return sorted[index]
}

func CalculateMaxConsecutiveLosses(trades []Trade) int {
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