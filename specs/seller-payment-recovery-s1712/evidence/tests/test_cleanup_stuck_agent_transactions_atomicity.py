"""Actual scheduled candidate rollback, distinct from read-scan rollback."""
from contextlib import asynccontextmanager
import inspect

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession
from test_order_money_protocol import db, migrated_protocol
from test_refund_processing_protocol import f6_pending_agent, f6_snapshot


@pytest.mark.asyncio
async def test_cleanup_stuck_agent_transactions_rolls_back_on_mid_execution_failure(db, monkeypatch):
    from app.tasks import scheduled
    function=inspect.unwrap(scheduled.cleanup_stuck_agent_transactions.run)
    async def task():
        return await function(None) if len(inspect.signature(function).parameters) else await function()
    for boundary in ('order', 'spend'):
        oid,tid,key,pi,ch=await f6_pending_agent(db,monkeypatch)
        before=await f6_snapshot(db,oid,tid,key)
        await db.rollback()
        closed=[]
        @asynccontextmanager
        async def owned():
            try:
                async with AsyncSession(db.bind,expire_on_commit=False) as session:
                    yield session
            finally:
                closed.append(True)
        monkeypatch.setattr(scheduled,'AsyncSessionLocal',owned)
        reached=[]
        def inject(conn,cursor,statement,parameters,context,executemany):
            normalized=' '.join(statement.lower().split())
            if (boundary=='order' and normalized.startswith('update orders') or
                    boundary=='spend' and normalized.startswith('update agent_api_keys')):
                reached.append(normalized)
                raise RuntimeError('mid-execution failure '+boundary)
        event.listen(db.bind.sync_engine,'after_cursor_execute',inject)
        try:
            with pytest.raises(RuntimeError,match='mid-execution failure '+boundary):
                await task()
        finally:
            event.remove(db.bind.sync_engine,'after_cursor_execute',inject)
        assert reached and closed==[True]
        assert await f6_snapshot(db,oid,tid,key)==before
        # A fresh independent session proves the failed context released locks.
        async with AsyncSession(db.bind) as observer:
            await observer.execute(text('SELECT id FROM orders WHERE id=:id FOR UPDATE NOWAIT'),{'id':oid})
            await observer.execute(text('SELECT id FROM transactions WHERE id=:id FOR UPDATE NOWAIT'),{'id':tid})
            await observer.execute(text('SELECT id FROM agent_api_keys WHERE id=:id FOR UPDATE NOWAIT'),{'id':key})
        await db.rollback()
        await task()
        assert await db.scalar(text('SELECT spend_used FROM agent_api_keys WHERE id=:id'),{'id':key})==0
        assert await db.scalar(text('SELECT status FROM transactions WHERE id=:id'),{'id':tid})=='cancelled'
        after=await f6_snapshot(db,oid,tid,key)
        await db.rollback()
        await task()
        assert await f6_snapshot(db,oid,tid,key)==after
        await db.rollback()
