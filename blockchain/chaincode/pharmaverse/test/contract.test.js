'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const PharmaVerseContract = require('../contract');

function context(initial = {}) {
    const state = new Map(
        Object.entries(initial).map(([key, value]) => [
            key,
            Buffer.from(JSON.stringify(value))
        ])
    );
    const history = new Map();
    let transaction = 0;
    let activeTransactionId = null;
    return {
        state,
        stub: {
            async getState(key) {
                return state.get(key) || Buffer.alloc(0);
            },
            async putState(key, value) {
                const bytes = Buffer.from(value);
                state.set(key, bytes);
                const records = history.get(key) || [];
                records.push({
                    txId: activeTransactionId,
                    timestamp: { seconds: 1_798_000_000, nanos: 0 },
                    isDelete: false,
                    value: bytes
                });
                history.set(key, records);
            },
            getTxID() {
                transaction += 1;
                activeTransactionId = `tx-${transaction}`;
                return activeTransactionId;
            },
            getTxTimestamp() {
                return { seconds: 1_798_000_000, nanos: 0 };
            },
            async getStateByRange() {
                const entries = [...state.entries()].sort(([a], [b]) => a.localeCompare(b));
                let index = 0;
                return {
                    async next() {
                        if (index >= entries.length) return { done: true };
                        const [key, value] = entries[index++];
                        return { done: false, value: { key, value } };
                    },
                    async close() {}
                };
            },
            async getHistoryForKey(key) {
                const entries = history.get(key) || [];
                let index = 0;
                return {
                    async next() {
                        if (index >= entries.length) return { done: true };
                        return { done: false, value: entries[index++] };
                    },
                    async close() {}
                };
            }
        },
        history
    };
}

const drugState = { 'DRUG-1': { drugId: 'DRUG-1' } };

test('legacy createBatch arguments retain deterministic identity defaults', async () => {
    const ctx = context(drugState);
    const raw = await new PharmaVerseContract().createBatch(
        ctx, 'BATCH-1', 'DRUG-1', 'Example Manufacturer', '10', '2026-01-01', '2028-01-01'
    );

    const batch = JSON.parse(raw);
    assert.equal(batch.qrId, 'QR-MED-BATCH-1');
    assert.equal(batch.rfidId, 'RFID-MED-BATCH-1');
});

test('createBatch accepts explicit existing identity identifiers', async () => {
    const ctx = context(drugState);
    const raw = await new PharmaVerseContract().createBatch(
        ctx, 'BATCH-1', 'DRUG-1', 'Example Manufacturer', '10', '2026-01-01', '2028-01-01',
        'QR-MED-000001', 'RFID-MED-000001'
    );

    const batch = JSON.parse(raw);
    assert.equal(batch.qrId, 'QR-MED-000001');
    assert.equal(batch.rfidId, 'RFID-MED-000001');
});

test('createBatch rejects a partial QR/RFID pair without writing state', async () => {
    const ctx = context(drugState);
    await assert.rejects(
        () => new PharmaVerseContract().createBatch(
            ctx, 'BATCH-1', 'DRUG-1', 'Example Manufacturer', '10', '2026-01-01', '2028-01-01',
            'QR-1'
        ),
        /must be supplied together/
    );
    assert.equal(ctx.state.has('BATCH-1'), false);
});

test('createBatch rejects an identity already used by another ledger batch', async () => {
    const ctx = context({
        ...drugState,
        'BATCH-EXISTING': {
            batchId: 'BATCH-EXISTING', qrId: 'QR-EXISTING', rfidId: 'RFID-EXISTING'
        }
    });
    await assert.rejects(
        () => new PharmaVerseContract().createBatch(
            ctx, 'BATCH-NEW', 'DRUG-1', 'Example Manufacturer', '10', '2026-01-01', '2028-01-01',
            'QR-EXISTING', 'RFID-NEW'
        ),
        /already assigned/
    );
    assert.equal(ctx.state.has('BATCH-NEW'), false);
});

test('identity assignment rejects duplicate identifiers already on the ledger', async () => {
    const ctx = context({
        'BATCH-1': { batchId: 'BATCH-1' },
        'BATCH-2': { batchId: 'BATCH-2', qrId: 'QR-USED', rfidId: 'RFID-USED' }
    });
    await assert.rejects(
        () => new PharmaVerseContract().assignIdentity(ctx, 'BATCH-1', 'QR-USED', 'RFID-NEW'),
        /already assigned/
    );
    assert.equal(JSON.parse(ctx.state.get('BATCH-1').toString()).qrId, undefined);
});

test('batch history includes selected IoT, AI, and ownership audit records', async () => {
    const ctx = context({
        'BATCH-1': {
            batchId: 'BATCH-1',
            currentOwner: 'manufacturer',
            auditEvents: []
        }
    });
    const contract = new PharmaVerseContract();

    await contract.recordIoTEvent(ctx, 'BATCH-1', 'SHIP-1', 5, 45, 12, 77, 'moving', 'RFID-1');
    await contract.recordAIAlert(ctx, 'BATCH-1', 'SHIP-1', 'RISK', 80, 'Evidence summary', 'AI');
    await contract.transferDrug(ctx, 'BATCH-1', 'manufacturer', 'distributor');

    const history = JSON.parse(await contract.getBatchHistory(ctx, 'BATCH-1'));
    const selectedTypes = history
        .map((entry) => entry.recordType)
        .filter((recordType) => recordType !== 'BATCH_STATE');

    assert.deepEqual(selectedTypes, ['IOT_EVENT', 'AI_ALERT', 'OWNERSHIP_TRANSFER']);
    assert.equal(history.find((entry) => entry.recordType === 'IOT_EVENT').value.batchId, 'BATCH-1');
    assert.equal(history.find((entry) => entry.recordType === 'AI_ALERT').value.riskScore, 80);
    assert.equal(history.find((entry) => entry.recordType === 'OWNERSHIP_TRANSFER').value.to, 'distributor');
});
