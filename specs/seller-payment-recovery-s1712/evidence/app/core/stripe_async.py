"""
Async Stripe Client Wrapper
===========================

PURPOSE:
    Wraps synchronous Stripe library calls in a thread pool executor
    to prevent blocking the main asyncio event loop.

USAGE:
    from app.core.stripe_async import run_stripe
    account = await run_stripe(stripe.Account.retrieve, account_id)

PHASE: 3.H.2
CREATED: 2026-01-26
"""

import stripe
import asyncio
from functools import partial
from typing import TypeVar, Callable
from app.core.config import settings

# Initialize Stripe globally
stripe.api_key = settings.stripe_secret_key

T = TypeVar("T")


def stripe_secret_key_for_actor(*, synthetic_actor: bool = False) -> str:
    """Select the Stripe key for an actor before network I/O.

    Synthetic E2E actors may only use the configured Stripe test key. A missing
    or live key is a hard refusal so production credentials are never used for
    synthetic checkout/connect paths.
    """

    if synthetic_actor:
        key = settings.STRIPE_TEST_SECRET_KEY
        if not key or not key.startswith("sk_test_"):
            raise RuntimeError("Synthetic Stripe operations require STRIPE_TEST_SECRET_KEY starting with sk_test_")
        return key
    return settings.stripe_secret_key


async def run_stripe(func: Callable[..., T], *args, synthetic_actor: bool = False, **kwargs) -> T:
    """
    Execute a synchronous Stripe API call in a separate thread.
    
    Args:
        func: The synchronous Stripe function to call (e.g., stripe.Account.retrieve)
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        The result of the Stripe API call
    """
    loop = asyncio.get_running_loop()
    if synthetic_actor:
        kwargs.setdefault("api_key", stripe_secret_key_for_actor(synthetic_actor=True))
    # partial allows passing kwargs to the function which run_in_executor doesn't support directly
    pfunc = partial(func, *args, **kwargs)
    return await loop.run_in_executor(None, pfunc)
