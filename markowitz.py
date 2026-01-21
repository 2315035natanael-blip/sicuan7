import numpy as np

def markowitz_optimize(returns, cov_matrix, risk_aversion=1):
    n = len(returns)

    # simple quadratic optimization closed form (no constraints)
    inv_cov = np.linalg.inv(cov_matrix)
    ones = np.ones(n)

    weights = inv_cov @ returns
    weights = weights / np.sum(weights)

    weights = np.maximum(weights, 0)
    weights = weights / np.sum(weights)

    return weights.tolist()
