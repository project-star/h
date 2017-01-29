# -*- coding: utf-8 -*-

import click

from memex.search import index


@click.command()
@click.pass_context
def createsharedindex(ctx):
    """
    Reindex all annotations from the PostgreSQL database to the Elasticsearch index.
    """

    request = ctx.obj['bootstrap']()

    index.createsharedindex(request.db, request.es, request)
