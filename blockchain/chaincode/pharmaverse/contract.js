'use strict';

const { Contract } = require('fabric-contract-api');

async function assertIdentityPairUnique(ctx, qrId, rfidId, excludedBatchId = null) {
    if (!qrId || !qrId.trim() || !rfidId || !rfidId.trim()) {
        throw new Error('QR and RFID identifiers are required');
    }
    if (qrId === rfidId) {
        throw new Error('QR and RFID identifiers must be different');
    }

    const iterator = await ctx.stub.getStateByRange('', '');
    try {
        while (true) {
            const result = await iterator.next();
            if (result.done) break;
            const entry = result.value;
            if (!entry || entry.key === excludedBatchId || !entry.value) continue;

            let asset;
            try {
                asset = JSON.parse(entry.value.toString());
            } catch {
                continue;
            }
            if (!asset || !asset.batchId || entry.key !== asset.batchId) continue;
            if (asset.qrId === qrId || asset.rfidId === qrId ||
                asset.qrId === rfidId || asset.rfidId === rfidId) {
                throw new Error('QR or RFID identifier is already assigned');
            }
        }
    } finally {
        await iterator.close();
    }
}

class PharmaVerseContract extends Contract {

    // ============================================================
    // HELPER
    // ============================================================

    getTransactionTimestamp(ctx) {
        const timestamp = ctx.stub.getTxTimestamp();

        const seconds = Number(timestamp.seconds);
        const nanos = Number(timestamp.nanos || 0);

        return new Date(
            (seconds * 1000) + Math.floor(nanos / 1000000)
        ).toISOString();
    }

    addBatchAuditReference(batch, type, key, transactionId, timestamp) {
        batch.auditEvents = Array.isArray(batch.auditEvents) ? batch.auditEvents : [];
        batch.auditEvents.push({ type, key, transactionId, timestamp });
    }

    // ============================================================
    // DRUG FUNCTIONS
    // ============================================================

    async registerDrug(ctx, drugId, name, strength, manufacturer) {
        const existingDrug = await ctx.stub.getState(drugId);

        if (existingDrug && existingDrug.length > 0) {
            throw new Error(`Drug ${drugId} already exists`);
        }

        const txId = ctx.stub.getTxID();

        const drug = {
            drugId,
            name,
            strength,
            manufacturer,
            status: 'REGISTERED',
            registeredAt: this.getTransactionTimestamp(ctx),
            transactionId: txId
        };

        await ctx.stub.putState(
            drugId,
            Buffer.from(JSON.stringify(drug))
        );

        return JSON.stringify(drug);
    }

    async getDrug(ctx, drugId) {
        const drugBytes = await ctx.stub.getState(drugId);

        if (!drugBytes || drugBytes.length === 0) {
            throw new Error(`Drug ${drugId} does not exist`);
        }

        return drugBytes.toString();
    }

    // ============================================================
    // BATCH FUNCTIONS
    // ============================================================

    async createBatch(
        ctx,
        batchId,
        drugId,
        manufacturer,
        quantity,
        manufacturedDate,
        expiryDate,
        qrId,
        rfidId
    ) {
        const existingBatch = await ctx.stub.getState(batchId);

        if (existingBatch && existingBatch.length > 0) {
            throw new Error(`Batch ${batchId} already exists`);
        }

        const drugBytes = await ctx.stub.getState(drugId);

        if (!drugBytes || drugBytes.length === 0) {
            throw new Error(`Drug ${drugId} does not exist`);
        }

        if ((qrId && !rfidId) || (!qrId && rfidId)) {
            throw new Error('QR and RFID identifiers must be supplied together');
        }
        const resolvedQrId = qrId || `QR-MED-${batchId}`;
        const resolvedRfidId = rfidId || `RFID-MED-${batchId}`;
        await assertIdentityPairUnique(ctx, resolvedQrId, resolvedRfidId);

        const txId = ctx.stub.getTxID();

        const batch = {
            batchId,
            drugId,
            manufacturer,
            quantity,
            manufacturedDate,
            expiryDate,
            qrId: resolvedQrId,
            rfidId: resolvedRfidId,
            currentOwner: manufacturer,
            status: 'CREATED',
            transactionId: txId
        };

        await ctx.stub.putState(
            batchId,
            Buffer.from(JSON.stringify(batch))
        );

        return JSON.stringify(batch);
    }

    async getBatch(ctx, batchId) {
        const batchBytes = await ctx.stub.getState(batchId);

        if (!batchBytes || batchBytes.length === 0) {
            throw new Error(`Batch ${batchId} does not exist`);
        }

        return batchBytes.toString();
    }

    // ============================================================
    // QR / RFID FUNCTIONS
    // ============================================================

    async assignIdentity(ctx, batchId, qrId, rfidId) {
        const batchBytes = await ctx.stub.getState(batchId);

        if (!batchBytes || batchBytes.length === 0) {
            throw new Error(`Batch ${batchId} does not exist`);
        }

        const batch = JSON.parse(batchBytes.toString());

        if (batch.qrId || batch.rfidId) {
            throw new Error(`Identity already assigned to batch ${batchId}`);
        }

        await assertIdentityPairUnique(ctx, qrId, rfidId, batchId);

        const txId = ctx.stub.getTxID();

        batch.qrId = qrId;
        batch.rfidId = rfidId;
        batch.identityTransactionId = txId;
        batch.identityAssignedAt = this.getTransactionTimestamp(ctx);

        await ctx.stub.putState(
            batchId,
            Buffer.from(JSON.stringify(batch))
        );

        return JSON.stringify({
            batchId,
            qrId,
            rfidId,
            transactionId: txId
        });
    }

    async verifyIdentity(ctx, batchId, qrId, rfidId) {
        const batchBytes = await ctx.stub.getState(batchId);

        if (!batchBytes || batchBytes.length === 0) {
            return JSON.stringify({
                result: 'INVALID',
                reason: `Batch ${batchId} does not exist`
            });
        }

        const batch = JSON.parse(batchBytes.toString());

        const qrMatch = batch.qrId === qrId;
        const rfidMatch = batch.rfidId === rfidId;

        if (qrMatch && rfidMatch) {
            return JSON.stringify({
                result: 'AUTHENTIC',
                batchId,
                qrId,
                rfidId,
                qrMatch: true,
                rfidMatch: true,
                currentOwner: batch.currentOwner,
                status: batch.status
            });
        }

        if (!qrMatch && !rfidMatch) {
            return JSON.stringify({
                result: 'POTENTIAL_COUNTERFEIT',
                batchId,
                qrId,
                rfidId,
                qrMatch: false,
                rfidMatch: false
            });
        }

        return JSON.stringify({
            result: 'SUSPICIOUS',
            batchId,
            qrId,
            rfidId,
            qrMatch,
            rfidMatch
        });
    }
    // ============================================================
    // IoT FUNCTIONS
    // ============================================================

    async recordIoTEvent(
        ctx,
        batchId,
        shipmentId,
        temperature,
        humidity,
        latitude,
        longitude,
        movement,
        rfidId
    ) {
        const batchBytes = await ctx.stub.getState(batchId);

        if (!batchBytes || batchBytes.length === 0) {
            throw new Error(`Batch ${batchId} does not exist`);
        }

        const batch = JSON.parse(batchBytes.toString());

        const txId = ctx.stub.getTxID();

        const iotEvent = {
            eventId: `IOT_${txId}`,
            batchId,
            shipmentId,
            temperature: Number(temperature),
            humidity: Number(humidity),
            latitude: Number(latitude),
            longitude: Number(longitude),
            movement,
            rfidId,
            recordedAt: this.getTransactionTimestamp(ctx),
            transactionId: txId
        };

        await ctx.stub.putState(
            iotEvent.eventId,
            Buffer.from(JSON.stringify(iotEvent))
        );
        this.addBatchAuditReference(
            batch,
            'IOT_EVENT',
            iotEvent.eventId,
            txId,
            iotEvent.recordedAt
        );
        await ctx.stub.putState(batchId, Buffer.from(JSON.stringify(batch)));

        return JSON.stringify(iotEvent);
    }

    async getIoTEvent(ctx, eventId) {
        const eventBytes = await ctx.stub.getState(eventId);

        if (!eventBytes || eventBytes.length === 0) {
            throw new Error(`IoT event ${eventId} does not exist`);
        }

        return eventBytes.toString();
    }
    // ============================================================
    // AI ALERT FUNCTIONS
    // ============================================================

    async recordAIAlert(
        ctx,
        batchId,
        shipmentId,
        alertType,
        riskScore,
        explanation,
        detectedBy
    ) {
        const batchBytes = await ctx.stub.getState(batchId);

        if (!batchBytes || batchBytes.length === 0) {
            throw new Error(`Batch ${batchId} does not exist`);
        }

        const batch = JSON.parse(batchBytes.toString());
        const txId = ctx.stub.getTxID();

        const aiAlert = {
            alertId: `AI_ALERT_${txId}`,
            batchId,
            shipmentId,
            alertType,
            riskScore: Number(riskScore),
            explanation,
            detectedBy,
            detectedAt: this.getTransactionTimestamp(ctx),
            transactionId: txId
        };

        await ctx.stub.putState(
            aiAlert.alertId,
            Buffer.from(JSON.stringify(aiAlert))
        );
        this.addBatchAuditReference(
            batch,
            'AI_ALERT',
            aiAlert.alertId,
            txId,
            aiAlert.detectedAt
        );
        await ctx.stub.putState(batchId, Buffer.from(JSON.stringify(batch)));

        return JSON.stringify(aiAlert);
    }

    async getAIAlert(ctx, alertId) {
        const alertBytes = await ctx.stub.getState(alertId);

        if (!alertBytes || alertBytes.length === 0) {
            throw new Error(`AI alert ${alertId} does not exist`);
        }

        return alertBytes.toString();
    }

    // ============================================================
    // PROVENANCE / HISTORY FUNCTIONS
    // ============================================================

    async getBatchHistory(ctx, batchId) {
        const batchBytes = await ctx.stub.getState(batchId);

        if (!batchBytes || batchBytes.length === 0) {
            throw new Error(`Batch ${batchId} does not exist`);
        }

        const batch = JSON.parse(batchBytes.toString());
        const iterator = await ctx.stub.getHistoryForKey(batchId);
        const history = [];

        let result = await iterator.next();

        while (!result.done) {
            const record = result.value;

            history.push({
                transactionId: record.txId,
                timestamp: record.timestamp
                    ? new Date(
                        (Number(record.timestamp.seconds) * 1000) +
                        Math.floor(Number(record.timestamp.nanos || 0) / 1000000)
                    ).toISOString()
                    : null,
                isDelete: record.isDelete,
                recordType: 'BATCH_STATE',
                value: record.isDelete
                    ? null
                    : JSON.parse(record.value.toString())
            });

            result = await iterator.next();
        }

        await iterator.close();

        for (const reference of batch.auditEvents || []) {
            const eventBytes = await ctx.stub.getState(reference.key);
            if (!eventBytes || eventBytes.length === 0) continue;
            history.push({
                transactionId: reference.transactionId,
                timestamp: reference.timestamp,
                isDelete: false,
                recordType: reference.type,
                value: JSON.parse(eventBytes.toString())
            });
        }

        history.sort((first, second) =>
            String(first.timestamp || '').localeCompare(String(second.timestamp || ''))
        );
        return JSON.stringify(history);
    }
    // ============================================================
    // COUNTERFEIT / FLAG FUNCTIONS
    // ============================================================

    async flagDrug(
        ctx,
        batchId,
        reason,
        riskLevel,
        flaggedBy
    ) {
        const batchBytes = await ctx.stub.getState(batchId);

        if (!batchBytes || batchBytes.length === 0) {
            throw new Error(`Batch ${batchId} does not exist`);
        }

        const batch = JSON.parse(batchBytes.toString());

        const txId = ctx.stub.getTxID();
        const flaggedAt = this.getTransactionTimestamp(ctx);

        const flag = {
            flagId: `FLAG_${txId}`,
            batchId,
            reason,
            riskLevel,
            flaggedBy,
            flaggedAt,
            transactionId: txId,
            previousStatus: batch.status
        };

        batch.status = 'FLAGGED';
        batch.flagged = true;
        batch.lastFlagTransactionId = txId;

        await ctx.stub.putState(
            batchId,
            Buffer.from(JSON.stringify(batch))
        );

        await ctx.stub.putState(
            flag.flagId,
            Buffer.from(JSON.stringify(flag))
        );

        return JSON.stringify(flag);
    }

    async getFlag(ctx, flagId) {
        const flagBytes = await ctx.stub.getState(flagId);

        if (!flagBytes || flagBytes.length === 0) {
            throw new Error(`Flag ${flagId} does not exist`);
        }

        return flagBytes.toString();
    }

    // ============================================================
    // SHIPMENT FUNCTIONS
    // ============================================================

    async shipDrug(
        ctx,
        shipmentId,
        batchId,
        from,
        to,
        transporter
    ) {
        const existingShipment = await ctx.stub.getState(shipmentId);

        if (existingShipment && existingShipment.length > 0) {
            throw new Error(`Shipment ${shipmentId} already exists`);
        }

        const batchBytes = await ctx.stub.getState(batchId);

        if (!batchBytes || batchBytes.length === 0) {
            throw new Error(`Batch ${batchId} does not exist`);
        }

        const batch = JSON.parse(batchBytes.toString());

        const txId = ctx.stub.getTxID();
        const transactionTime = this.getTransactionTimestamp(ctx);

        const shipment = {
            shipmentId,
            batchId,
            from,
            to,
            transporter,
            status: 'SHIPPED',
            shippedAt: transactionTime,
            transactionId: txId
        };

        batch.status = 'IN_TRANSIT';
        batch.currentOwner = transporter;

        await ctx.stub.putState(
            batchId,
            Buffer.from(JSON.stringify(batch))
        );

        await ctx.stub.putState(
            shipmentId,
            Buffer.from(JSON.stringify(shipment))
        );

        return JSON.stringify(shipment);
    }

    async receiveDrug(ctx, shipmentId, receiver) {
        const shipmentBytes = await ctx.stub.getState(shipmentId);

        if (!shipmentBytes || shipmentBytes.length === 0) {
            throw new Error(`Shipment ${shipmentId} does not exist`);
        }

        const shipment = JSON.parse(shipmentBytes.toString());

        if (shipment.status === 'RECEIVED') {
            throw new Error(
                `Shipment ${shipmentId} has already been received`
            );
        }

        const batchBytes = await ctx.stub.getState(shipment.batchId);

        if (!batchBytes || batchBytes.length === 0) {
            throw new Error(`Batch ${shipment.batchId} does not exist`);
        }

        const batch = JSON.parse(batchBytes.toString());

        const txId = ctx.stub.getTxID();
        const transactionTime = this.getTransactionTimestamp(ctx);

        shipment.status = 'RECEIVED';
        shipment.receiver = receiver;
        shipment.receivedAt = transactionTime;
        shipment.receiveTransactionId = txId;

        batch.status = 'RECEIVED';
        batch.currentOwner = receiver;

        await ctx.stub.putState(
            shipment.shipmentId,
            Buffer.from(JSON.stringify(shipment))
        );

        await ctx.stub.putState(
            batch.batchId,
            Buffer.from(JSON.stringify(batch))
        );

        return JSON.stringify(shipment);
    }

    async getShipment(ctx, shipmentId) {
        const shipmentBytes = await ctx.stub.getState(shipmentId);

        if (!shipmentBytes || shipmentBytes.length === 0) {
            throw new Error(`Shipment ${shipmentId} does not exist`);
        }

        return shipmentBytes.toString();
    }

    // ============================================================
    // TRANSFER FUNCTION
    // ============================================================

    async transferDrug(ctx, batchId, from, to) {
        const batchBytes = await ctx.stub.getState(batchId);

        if (!batchBytes || batchBytes.length === 0) {
            throw new Error(`Batch ${batchId} does not exist`);
        }

        const batch = JSON.parse(batchBytes.toString());

        if (batch.currentOwner !== from) {
            throw new Error(
                `Unauthorized transfer. Current owner is ${batch.currentOwner}`
            );
        }

        const txId = ctx.stub.getTxID();
        const transactionTime = this.getTransactionTimestamp(ctx);

        const transfer = {
            batchId,
            from,
            to,
            transferredAt: transactionTime,
            transactionId: txId
        };

        const transferKey = `TRANSFER_${txId}`;
        batch.currentOwner = to;
        batch.status = 'TRANSFERRED';
        batch.lastTransferTransactionId = txId;
        this.addBatchAuditReference(
            batch,
            'OWNERSHIP_TRANSFER',
            transferKey,
            txId,
            transactionTime
        );

        await ctx.stub.putState(
            transferKey,
            Buffer.from(JSON.stringify(transfer))
        );
        await ctx.stub.putState(batchId, Buffer.from(JSON.stringify(batch)));

        return JSON.stringify(transfer);
    }
}

module.exports = PharmaVerseContract;
