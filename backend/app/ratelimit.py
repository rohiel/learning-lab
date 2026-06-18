"""Shared rate limiter (slowapi).

Kept in its own module so both `main` and the routers can import the same
instance without a circular import. Generation/help endpoints get modest
limits; expands in later phases as public endpoints land.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
