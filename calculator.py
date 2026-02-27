"""Crypto futures risk calculator CLI.

This script prompts for trade and account inputs, validates numeric values,
and prints readable risk metrics for a planned futures position.
"""


def get_positive_float(prompt: str) -> float:
    """Prompt until the user provides a positive floating-point number."""
    while True:
        raw_value = input(prompt).strip()
        try:
            value = float(raw_value)
        except ValueError:
            print("Invalid input. Please enter a numeric value.")
            continue

        if value <= 0:
            print("Value must be greater than 0.")
            continue

        return value


def calculate_metrics(
    account_balance: float,
    leverage: float,
    entry_price: float,
    stop_loss_price: float,
    risk_percent: float,
) -> dict:
    """Calculate position sizing and risk metrics.

    Calculations used:
    - Dollar risk amount = account_balance * (risk_percent / 100)
    - Risk per unit = abs(entry_price - stop_loss_price)
    - Quantity based on risk = dollar_risk / risk_per_unit
    - Notional size = quantity * entry_price
    - Max notional available from leverage = account_balance * leverage
    - Recommended notional = min(notional size, max notional)

    Liquidation estimate is a simplified approximation using:
    - Long:  entry * (1 - 1/leverage + maintenance_margin_rate)
    - Short: entry * (1 + 1/leverage - maintenance_margin_rate)
    where maintenance_margin_rate is assumed 0.5%.

    Risk-to-reward ratio is shown against a default 2R target
    (target move = 2 * risk distance) because take-profit is not requested.
    """
    dollar_risk = account_balance * (risk_percent / 100)
    risk_per_unit = abs(entry_price - stop_loss_price)

    if risk_per_unit == 0:
        raise ValueError("Entry price and stop loss price cannot be equal.")

    side = "LONG" if stop_loss_price < entry_price else "SHORT"

    raw_quantity = dollar_risk / risk_per_unit
    raw_notional = raw_quantity * entry_price

    max_notional = account_balance * leverage
    recommended_notional = min(raw_notional, max_notional)
    recommended_quantity = recommended_notional / entry_price

    # Actual risk can differ if notional must be capped by leverage limits.
    actual_dollar_risk = recommended_quantity * risk_per_unit
    actual_risk_percent = (actual_dollar_risk / account_balance) * 100

    maintenance_margin_rate = 0.005
    if side == "LONG":
        liquidation_price = entry_price * (1 - (1 / leverage) + maintenance_margin_rate)
        default_take_profit = entry_price + (2 * risk_per_unit)
        reward_per_unit = default_take_profit - entry_price
    else:
        liquidation_price = entry_price * (1 + (1 / leverage) - maintenance_margin_rate)
        default_take_profit = entry_price - (2 * risk_per_unit)
        reward_per_unit = entry_price - default_take_profit

    risk_to_reward = reward_per_unit / risk_per_unit if risk_per_unit else 0

    return {
        "side": side,
        "dollar_risk_target": dollar_risk,
        "recommended_quantity": recommended_quantity,
        "recommended_notional": recommended_notional,
        "max_notional_allowed": max_notional,
        "liquidation_price": liquidation_price,
        "actual_dollar_risk": actual_dollar_risk,
        "actual_risk_percent": actual_risk_percent,
        "risk_to_reward": risk_to_reward,
        "default_take_profit": default_take_profit,
    }


def main() -> None:
    """CLI entrypoint."""
    print("=" * 56)
    print("        Crypto Futures Risk Calculator (CLI)")
    print("=" * 56)

    account_balance = get_positive_float("Account balance (USD): ")
    leverage = get_positive_float("Leverage (e.g., 10 for 10x): ")
    entry_price = get_positive_float("Entry price: ")
    stop_loss_price = get_positive_float("Stop loss price: ")
    risk_percent = get_positive_float("Risk percentage per trade (%): ")

    if risk_percent >= 100:
        print("Risk percentage must be below 100%.")
        return

    try:
        metrics = calculate_metrics(
            account_balance=account_balance,
            leverage=leverage,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            risk_percent=risk_percent,
        )
    except ValueError as error:
        print(f"Error: {error}")
        return

    print("\n" + "-" * 56)
    print(f"Position side:                {metrics['side']}")
    print(f"Recommended position size:    {metrics['recommended_quantity']:.6f} units")
    print(f"Recommended notional size:    ${metrics['recommended_notional']:,.2f}")
    print(f"Dollar risk amount (target):  ${metrics['dollar_risk_target']:,.2f}")
    print(f"Max loss $ (est.):            ${metrics['actual_dollar_risk']:,.2f}")
    print(f"Risk % per trade (actual):    {metrics['actual_risk_percent']:.2f}%")
    print(f"Liquidation estimate:         ${metrics['liquidation_price']:,.2f}")
    print(f"Risk-to-reward ratio:         1:{metrics['risk_to_reward']:.2f}")
    print(f"(Assumed take-profit for R:R: ${metrics['default_take_profit']:,.2f})")

    if metrics["recommended_notional"] < (metrics["dollar_risk_target"] * entry_price / abs(entry_price - stop_loss_price)):
        print("\nNote: Position size was capped by leverage limits.")

    print("-" * 56)


if __name__ == "__main__":
    main()
