'use strict';

const http = require('http');
const { URL } = require('url');
const fabric = require('./fabricService');

function configuredPort(env = process.env) {
    return Number(env.FABRIC_GATEWAY_PORT || 8090);
}

const port = configuredPort();
const serviceSecret = process.env.FABRIC_GATEWAY_SECRET || '';

function json(response, statusCode, body) {
    response.writeHead(statusCode, {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': 'no-store'
    });
    response.end(JSON.stringify(body));
}

function success(data) {
    return { success: true, data };
}

function authorized(request) {
    return Boolean(serviceSecret) &&
        request.headers['x-pharmaverse-service-secret'] === serviceSecret;
}

function isMissingLedgerAsset(error) {
    const message = error instanceof Error ? error.message : String(error);
    return /\b(?:drug|batch|shipment|flag|AI alert)\b.+\bdoes not exist\b/i.test(message);
}

function isDuplicateLedgerAsset(error) {
    const message = error instanceof Error ? error.message : String(error);
    return /\b(?:drug|batch|shipment|flag|AI alert|identity|identifier)\b.+\balready (?:exists|assigned)\b/i.test(message);
}

function isInvalidTransitionOrOwner(error) {
    const message = error instanceof Error ? error.message : String(error);
    return /\b(?:unauthorized transfer|already been received|must be different|must be supplied together)\b/i.test(message);
}

function identifier(pathname, prefix) {
    if (!pathname.startsWith(prefix)) {
        return null;
    }
    const value = pathname.slice(prefix.length);
    return value && !value.includes('/') ? decodeURIComponent(value) : null;
}

function readJson(request) {
    return new Promise((resolve, reject) => {
        let body = '';
        request.setEncoding('utf8');
        request.on('data', chunk => {
            body += chunk;
            if (body.length > 10000) {
                reject(new Error('Request body too large'));
                request.destroy();
            }
        });
        request.on('end', () => {
            try {
                resolve(body ? JSON.parse(body) : {});
            } catch {
                reject(new Error('Malformed JSON request'));
            }
        });
        request.on('error', reject);
    });
}

async function handle(request, response) {
    const url = new URL(request.url, 'http://localhost');
    if (request.method === 'GET' && url.pathname === '/health') {
        return json(response, 200, success({
            status: 'ok',
            channel: fabric.config.channelName,
            chaincode: fabric.config.chaincodeName
        }));
    }
    if (!serviceSecret) {
        return json(response, 503, {
            success: false,
            error: { code: 'SERVICE_NOT_CONFIGURED', message: 'Gateway service secret is not configured' }
        });
    }
    if (!authorized(request)) {
        return json(response, 401, {
            success: false,
            error: { code: 'UNAUTHORIZED', message: 'Service authentication required' }
        });
    }

    let operation;
    if (request.method === 'GET') {
        const routes = [
            ['/api/drugs/', fabric.getDrug],
            ['/api/batches/', fabric.getBatch],
            ['/api/shipments/', fabric.getShipment],
            ['/api/flags/', fabric.getFlag],
            ['/api/iot-events/', fabric.getIoTEvent],
            ['/api/ai-alerts/', fabric.getAIAlert]
        ];
        for (const [prefix, handler] of routes) {
            const value = identifier(url.pathname, prefix);
            if (value !== null) {
                operation = () => handler(value);
                break;
            }
        }
        const historyMatch = url.pathname.match(/^\/api\/batches\/([^/]+)\/history$/);
        if (historyMatch) {
            operation = () => fabric.getBatchHistory(
                decodeURIComponent(historyMatch[1])
            );
        }
    } else if (request.method === 'POST') {
        let body;
        try {
            body = await readJson(request);
        } catch (error) {
            return json(response, 400, {
                success: false,
                error: { code: 'INVALID_REQUEST', message: error.message }
            });
        }
        const nonEmpty = (...values) => values.every(value =>
            typeof value === 'string' && value.length > 0
        );
        const required = (fields) => fields.every(field =>
            Object.prototype.hasOwnProperty.call(body, field) &&
            body[field] !== undefined && body[field] !== null &&
            (typeof body[field] !== 'string' || body[field].length > 0)
        );
        if (url.pathname === '/api/verify-identity' &&
            required(['batchId', 'qrId', 'rfidId']) &&
            nonEmpty(body.batchId, body.qrId, body.rfidId)) {
            operation = () => fabric.verifyIdentity(body.batchId, body.qrId, body.rfidId);
        } else if (url.pathname === '/api/drugs/register' &&
            required(['drugId', 'name', 'strength', 'manufacturer'])) {
            operation = () => fabric.registerDrug(
                body.drugId, body.name, body.strength, body.manufacturer
            );
        } else if (url.pathname === '/api/batches/create' &&
            required(['batchId', 'drugId', 'manufacturer', 'quantity', 'manufacturedDate', 'expiryDate']) &&
            ((body.qrId === undefined && body.rfidId === undefined) ||
                nonEmpty(body.qrId, body.rfidId))) {
            operation = () => fabric.createBatch(
                body.batchId, body.drugId, body.manufacturer, String(body.quantity),
                body.manufacturedDate, body.expiryDate, body.qrId, body.rfidId
            );
        } else if (url.pathname === '/api/identities/assign' &&
            required(['batchId', 'qrId', 'rfidId'])) {
            operation = () => fabric.assignIdentity(body.batchId, body.qrId, body.rfidId);
        } else if (url.pathname === '/api/iot-events' &&
            required(['batchId', 'shipmentId', 'temperature', 'humidity', 'latitude', 'longitude', 'movement', 'rfidId'])) {
            operation = () => fabric.recordIoTEvent(
                body.batchId, body.shipmentId, String(body.temperature), String(body.humidity),
                String(body.latitude), String(body.longitude), body.movement, body.rfidId
            );
        } else if (url.pathname === '/api/ai-alerts' &&
            required(['batchId', 'shipmentId', 'alertType', 'riskScore', 'explanation', 'detectedBy'])) {
            operation = () => fabric.recordAIAlert(
                body.batchId, body.shipmentId, body.alertType, String(body.riskScore),
                body.explanation, body.detectedBy
            );
        } else if (url.pathname === '/api/flags' &&
            required(['batchId', 'reason', 'riskLevel', 'flaggedBy'])) {
            operation = () => fabric.flagDrug(
                body.batchId, body.reason, body.riskLevel, body.flaggedBy
            );
        } else if (url.pathname === '/api/shipments/ship' &&
            required(['shipmentId', 'batchId', 'from', 'to', 'transporter'])) {
            operation = () => fabric.shipDrug(
                body.shipmentId, body.batchId, body.from, body.to, body.transporter
            );
        } else if (url.pathname === '/api/shipments/receive' &&
            required(['shipmentId', 'receiver'])) {
            operation = () => fabric.receiveDrug(body.shipmentId, body.receiver);
        } else if (url.pathname === '/api/shipments/transfer' &&
            required(['batchId', 'from', 'to'])) {
            operation = () => fabric.transferDrug(body.batchId, body.from, body.to);
        } else if (url.pathname === '/api/verify-identity') {
            return json(response, 400, {
                success: false,
                error: { code: 'INVALID_REQUEST', message: 'batchId, qrId, and rfidId are required' }
            });
        }
    }

    if (!operation) {
        return json(response, 404, {
            success: false,
            error: { code: 'NOT_FOUND', message: 'Gateway operation not found' }
        });
    }

    try {
        return json(response, 200, success(await operation()));
    } catch (error) {
        if (isMissingLedgerAsset(error)) {
            return json(response, 404, {
                success: false,
                error: {
                    code: 'ASSET_NOT_FOUND',
                    message: 'Ledger asset not found'
                }
            });
        }
        if (isDuplicateLedgerAsset(error)) {
            return json(response, 409, {
                success: false,
                error: {
                    code: 'ASSET_ALREADY_EXISTS',
                    message: error instanceof Error ? error.message : String(error)
                }
            });
        }
        if (isInvalidTransitionOrOwner(error)) {
            return json(response, 400, {
                success: false,
                error: {
                    code: 'INVALID_TRANSITION',
                    message: error instanceof Error ? error.message : String(error)
                }
            });
        }
        console.error('Fabric operation failed:', error.message);
        return json(response, 502, {
            success: false,
            error: { code: 'FABRIC_UNAVAILABLE', message: 'Fabric operation failed' }
        });
    }
}

function createServer() {
    return http.createServer((request, response) => {
        handle(request, response).catch(() => json(response, 500, {
            success: false,
            error: { code: 'INTERNAL_ERROR', message: 'Gateway request failed' }
        }));
    });
}

if (require.main === module) {
    createServer().listen(port, '127.0.0.1', () => {
        console.log(`PharmaVerse Fabric HTTP gateway listening on 127.0.0.1:${port}`);
    });
}

module.exports = { createServer, handle, configuredPort };
