"""Small persistence boundary for API routes.

Repositories deliberately keep Mongo-specific queries out of the HTTP layer so
the source and service contracts stay stable while storage details evolve.
"""
