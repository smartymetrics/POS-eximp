// Eximp & Cloves WhatsApp Support Line Gateway
// Multi-Device Baileys service with Cloudinary and Supabase Session Backup

import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import makeWASocket, { DisconnectReason, useMultiFileAuthState } from '@whiskeysockets/baileys';
import QRCode from 'qrcode';
import pino from 'pino';
import { v2 as cloudinary } from 'cloudinary';

// Global Process Resilience
process.on('uncaughtException', (err) => {
  console.warn('[WhatsApp Gateway] Handled uncaughtException:', err.message);
});
process.on('unhandledRejection', (reason) => {
  console.warn('[WhatsApp Gateway] Handled unhandledRejection:', reason);
});

// Load parent .env if present
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const parentEnvPath = path.resolve(__dirname, '..', '.env');
if (fs.existsSync(parentEnvPath)) {
  dotenv.config({ path: parentEnvPath });
} else {
  dotenv.config();
}

const PORT = process.env.WHATSAPP_GATEWAY_PORT || 8005;
const SUPPORT_LINE_ID = 'eximp_support_line';
const BASE_AUTH_DIR = path.resolve(__dirname, '.wa_auth');
const SESSION_DIR = path.join(BASE_AUTH_DIR, SUPPORT_LINE_ID);

// Configure Cloudinary if credentials exist
const hasCloudinary = Boolean(
  process.env.CLOUDINARY_CLOUD_NAME &&
  process.env.CLOUDINARY_API_KEY &&
  process.env.CLOUDINARY_API_SECRET
);

if (hasCloudinary) {
  cloudinary.config({
    cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
    api_key: process.env.CLOUDINARY_API_KEY,
    api_secret: process.env.CLOUDINARY_API_SECRET,
    secure: true,
  });
  console.log('[WhatsApp Gateway] Cloudinary configured for session persistence.');
} else {
  console.log('[WhatsApp Gateway] Cloudinary credentials not found in .env; will use local and Supabase session storage.');
}

// Global WhatsApp socket session state
const sessionState = {
  sock: null,
  status: 'disconnected', // 'disconnected' | 'connecting' | 'connected'
  qrCode: null,
  connectedUser: null,
  isInitializing: false,
  reconnectAttempts: 0,
  cloudSyncTimer: null,
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatPhoneToJid(phone) {
  if (!phone) return null;
  let clean = String(phone).replace(/[^0-9]/g, '');
  if (clean.startsWith('234')) {
    // Already in international format
  } else if (clean.startsWith('0')) {
    clean = '234' + clean.slice(1);
  } else if (clean.length === 10) {
    clean = '234' + clean;
  }
  if (clean.length < 10) return null;
  return `${clean}@s.whatsapp.net`;
}

function isAuthValid(creds) {
  if (!creds || typeof creds !== 'object') return false;
  return Boolean((creds.me && creds.me.id) || creds.registered === true);
}

function hasLocalAuth() {
  const credsPath = path.join(SESSION_DIR, 'creds.json');
  if (!fs.existsSync(credsPath)) return false;
  try {
    const creds = JSON.parse(fs.readFileSync(credsPath, 'utf8'));
    return isAuthValid(creds);
  } catch {
    return false;
  }
}

function clearLocalAuth() {
  try {
    if (fs.existsSync(SESSION_DIR)) {
      fs.rmSync(SESSION_DIR, { recursive: true, force: true });
      console.log('[WhatsApp Gateway] Local auth files cleared.');
    }
  } catch (err) {
    console.error('[WhatsApp Gateway] Error clearing local auth files:', err);
  }
}

// ── Cloud Session Persistence (Cloudinary & Supabase) ─────────────────────────

async function syncAuthToCloud() {
  if (!fs.existsSync(SESSION_DIR)) return false;
  const credsPath = path.join(SESSION_DIR, 'creds.json');
  if (!fs.existsSync(credsPath)) return false;

  try {
    const creds = JSON.parse(fs.readFileSync(credsPath, 'utf8'));
    if (!isAuthValid(creds)) {
      console.log('[WhatsApp Gateway] Skipping cloud backup: session not yet authenticated.');
      return false;
    }

    const files = fs.readdirSync(SESSION_DIR);
    if (!files.length) return false;

    const bundle = {};
    for (const file of files) {
      const filePath = path.join(SESSION_DIR, file);
      try {
        if (fs.statSync(filePath).isFile()) {
          bundle[file] = fs.readFileSync(filePath, 'utf8');
        }
      } catch (fErr) {}
    }

    const jsonString = JSON.stringify(bundle);

    // 1. Save to Cloudinary as raw asset
    if (hasCloudinary) {
      try {
        const base64Data = Buffer.from(jsonString).toString('base64');
        const dataUri = `data:application/json;base64,${base64Data}`;
        const result = await cloudinary.uploader.upload(dataUri, {
          resource_type: 'raw',
          public_id: 'wa_sessions/support_line_session.json',
          overwrite: true,
          invalidate: true,
        });
        console.log(`[WhatsApp Gateway] Successfully backed up session bundle to Cloudinary (${files.length} keys): ${result.secure_url}`);
      } catch (cErr) {
        console.warn('[WhatsApp Gateway] Cloudinary session upload error:', cErr.message);
      }
    }

    // 2. Also save to Supabase Storage if configured
    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseKey = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY;
    if (supabaseUrl && supabaseKey) {
      try {
        const uploadUrl = `${supabaseUrl}/storage/v1/object/signatures/wa_sessions/session_bundle.json`;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000);
        const res = await fetch(uploadUrl, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${supabaseKey}`,
            'Content-Type': 'application/json',
            'x-upsert': 'true',
          },
          body: jsonString,
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
        if (res.ok) {
          console.log(`[WhatsApp Gateway] Synced session bundle (${files.length} keys) to Supabase storage.`);
        }
      } catch (sErr) {
        console.warn('[WhatsApp Gateway] Supabase session upload error:', sErr.message);
      }
    }

    return true;
  } catch (err) {
    console.error('[WhatsApp Gateway] Failed to serialize session to cloud:', err.message);
    return false;
  }
}

async function restoreAuthFromCloud() {
  if (hasLocalAuth()) return true;

  console.log('[WhatsApp Gateway] Checking cloud storage for saved session bundle...');

  // 1. Try Cloudinary
  if (hasCloudinary) {
    try {
      const cloudUrl = cloudinary.url('wa_sessions/support_line_session.json', { resource_type: 'raw' });
      const res = await fetch(cloudUrl);
      if (res.ok) {
        const bundle = await res.json();
        if (bundle && bundle['creds.json']) {
          const creds = JSON.parse(bundle['creds.json']);
          if (isAuthValid(creds)) {
            if (!fs.existsSync(SESSION_DIR)) fs.mkdirSync(SESSION_DIR, { recursive: true });
            for (const [filename, content] of Object.entries(bundle)) {
              fs.writeFileSync(path.join(SESSION_DIR, filename), content, 'utf8');
            }
            console.log(`[WhatsApp Gateway] Successfully restored WhatsApp session from Cloudinary!`);
            return true;
          }
        }
      }
    } catch (cErr) {
      console.warn('[WhatsApp Gateway] Cloudinary session restore check:', cErr.message);
    }
  }

  // 2. Try Supabase Storage fallback
  const supabaseUrl = process.env.SUPABASE_URL;
  const supabaseKey = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY;
  if (supabaseUrl && supabaseKey) {
    try {
      const downloadUrl = `${supabaseUrl}/storage/v1/object/public/signatures/wa_sessions/session_bundle.json`;
      const res = await fetch(downloadUrl, {
        headers: { 'Authorization': `Bearer ${supabaseKey}` }
      });
      if (res.ok) {
        const bundle = await res.json();
        if (bundle && bundle['creds.json']) {
          const creds = JSON.parse(bundle['creds.json']);
          if (isAuthValid(creds)) {
            if (!fs.existsSync(SESSION_DIR)) fs.mkdirSync(SESSION_DIR, { recursive: true });
            for (const [filename, content] of Object.entries(bundle)) {
              fs.writeFileSync(path.join(SESSION_DIR, filename), content, 'utf8');
            }
            console.log(`[WhatsApp Gateway] Successfully restored WhatsApp session from Supabase storage!`);
            return true;
          }
        }
      }
    } catch (sErr) {
      console.warn('[WhatsApp Gateway] Supabase session restore check:', sErr.message);
    }
  }

  return false;
}

async function clearCloudSession() {
  if (hasCloudinary) {
    try {
      await cloudinary.uploader.destroy('wa_sessions/support_line_session.json', { resource_type: 'raw' });
      console.log('[WhatsApp Gateway] Cleared session bundle from Cloudinary.');
    } catch (e) {
      console.warn('[WhatsApp Gateway] Error clearing Cloudinary session:', e.message);
    }
  }

  const supabaseUrl = process.env.SUPABASE_URL;
  const supabaseKey = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY;
  if (supabaseUrl && supabaseKey) {
    try {
      const deleteUrl = `${supabaseUrl}/storage/v1/object/signatures/wa_sessions/session_bundle.json`;
      await fetch(deleteUrl, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${supabaseKey}` },
      });
      console.log('[WhatsApp Gateway] Cleared session bundle from Supabase.');
    } catch (e) {}
  }
}

function scheduleCloudSync() {
  if (sessionState.cloudSyncTimer) clearTimeout(sessionState.cloudSyncTimer);
  // Debounce 6 seconds to prevent hammering during bulk contact handshakes
  sessionState.cloudSyncTimer = setTimeout(() => {
    syncAuthToCloud().catch(err => console.warn('[WhatsApp Gateway] Debounced cloud sync error:', err.message));
  }, 6000);
}

// ── Baileys Connection Controller ────────────────────────────────────────────

async function connectSocket() {
  if (sessionState.status === 'connected' && sessionState.sock) {
    return getStatus();
  }

  if (sessionState.sock) {
    try {
      sessionState.sock.end(undefined);
    } catch {}
    sessionState.sock = null;
  }

  sessionState.isInitializing = true;
  sessionState.status = 'connecting';

  try {
    // 1. Attempt restore from cloud if not locally present
    if (!hasLocalAuth()) {
      await restoreAuthFromCloud();
    }

    if (!fs.existsSync(SESSION_DIR)) {
      fs.mkdirSync(SESSION_DIR, { recursive: true });
    }

    const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);

    sessionState.sock = makeWASocket({
      auth: state,
      logger: pino({ level: 'silent' }),
      printQRInTerminal: false,
      browser: ['Eximp & Cloves Support Line', 'Chrome', '1.0.0'],
      connectTimeoutMs: 60000,
      keepAliveIntervalMs: 25000,
    });

    sessionState.sock.ev.on('creds.update', async () => {
      try {
        await saveCreds();
        if (isAuthValid(state.creds)) {
          scheduleCloudSync();
        }
      } catch (e) {
        console.warn('[WhatsApp Gateway] Error updating creds:', e.message);
      }
    });

    sessionState.sock.ev.on('connection.update', async (update) => {
      const { connection, lastDisconnect, qr } = update;

      if (qr) {
        try {
          sessionState.qrCode = await QRCode.toDataURL(qr, { margin: 2, scale: 6 });
          sessionState.status = 'connecting';
          console.log('[WhatsApp Gateway] New pairing QR Code generated for Support Line.');
        } catch (err) {
          console.error('[WhatsApp Gateway] Failed to generate QR code data URL:', err);
        }
      }

      if (connection === 'close') {
        const statusCode = lastDisconnect?.error?.output?.statusCode;
        const isLoggedOut = statusCode === DisconnectReason.loggedOut;

        console.log(`[WhatsApp Gateway] Connection closed (code: ${statusCode}, loggedOut: ${isLoggedOut})`);

        if (!isLoggedOut) {
          const delay = Math.min(3000 * Math.pow(1.3, sessionState.reconnectAttempts), 25000);
          sessionState.reconnectAttempts++;
          sessionState.status = 'connecting';
          console.log(`[WhatsApp Gateway] Auto-reconnecting in ${Math.round(delay / 1000)}s (attempt ${sessionState.reconnectAttempts})...`);
          setTimeout(() => {
            sessionState.isInitializing = false;
            connectSocket().catch(e => console.warn('[WhatsApp Gateway] Reconnect attempt error:', e.message));
          }, delay);
        } else {
          sessionState.status = 'disconnected';
          sessionState.isInitializing = false;
          sessionState.reconnectAttempts = 0;
          sessionState.connectedUser = null;
          sessionState.qrCode = null;
          clearLocalAuth();
        }
      } else if (connection === 'open') {
        sessionState.status = 'connected';
        sessionState.qrCode = null;
        sessionState.reconnectAttempts = 0;
        sessionState.isInitializing = false;

        const user = sessionState.sock.user;
        const phone = user?.id ? user.id.split(':')[0] : '2349126864383';
        sessionState.connectedUser = {
          id: user?.id,
          name: user?.name || 'Eximp and Cloves infrastructure ltd',
          phone: phone,
        };

        console.log(`[WhatsApp Gateway] Support Line Connected Successfully: +${phone}`);

        try {
          await saveCreds();
        } catch {}
        setTimeout(() => {
          syncAuthToCloud().catch(e => console.warn('[WhatsApp Gateway] Initial cloud sync error:', e.message));
        }, 3000);
      }
    });

    sessionState.isInitializing = false;
    return getStatus();
  } catch (err) {
    console.error('[WhatsApp Gateway] Socket initialization failed:', err.message);
    sessionState.status = 'disconnected';
    sessionState.isInitializing = false;
    throw err;
  }
}

async function disconnectSocket() {
  try {
    if (sessionState.sock) {
      await sessionState.sock.logout().catch(() => {});
      sessionState.sock.end(undefined);
      sessionState.sock = null;
    }
  } catch (e) {
  } finally {
    sessionState.status = 'disconnected';
    sessionState.qrCode = null;
    sessionState.connectedUser = null;
    clearLocalAuth();
    await clearCloudSession();
  }
  return { success: true, message: 'WhatsApp support line disconnected and cloud session wiped.' };
}

async function sendMessage(phone, messageText, mediaUrl = null) {
  // If socket is in the middle of a reconnect, wait up to 4 seconds for it to settle
  if (sessionState.status === 'connecting' && sessionState.sock) {
    let waited = 0;
    while (sessionState.status === 'connecting' && waited < 4000) {
      await new Promise(r => setTimeout(r, 500));
      waited += 500;
    }
  }

  if (sessionState.status !== 'connected' || !sessionState.sock) {
    return {
      success: false,
      error: 'WhatsApp Support Line is currently reconnecting or unlinked. Please wait a moment and try again.',
    };
  }

  const jid = formatPhoneToJid(phone);
  if (!jid) {
    return { success: false, error: `Invalid destination phone number format: "${phone}"` };
  }

  try {
    if (mediaUrl && typeof mediaUrl === 'string' && mediaUrl.startsWith('http')) {
      const isVideo = /\.(mp4|mov|webm)(\?.*)?$/i.test(mediaUrl);
      if (isVideo) {
        await sessionState.sock.sendMessage(jid, {
          video: { url: mediaUrl },
          caption: messageText,
        });
      } else {
        await sessionState.sock.sendMessage(jid, {
          image: { url: mediaUrl },
          caption: messageText,
        });
      }
    } else {
      await sessionState.sock.sendMessage(jid, {
        text: messageText,
      });
    }

    console.log(`[WhatsApp Gateway] Dispatched WhatsApp message to ${phone}`);
    return { success: true, jid: jid };
  } catch (err) {
    console.error(`[WhatsApp Gateway] Failed to send message to ${phone}:`, err.message);
    return { success: false, error: err.message };
  }
}

function getStatus() {
  const localExists = hasLocalAuth();
  // If local auth exists with registered user, set connectedUser if missing
  if (localExists && !sessionState.connectedUser) {
    try {
      const credsPath = path.join(SESSION_DIR, 'creds.json');
      const creds = JSON.parse(fs.readFileSync(credsPath, 'utf8'));
      if (creds.me && creds.me.id) {
        const phone = creds.me.id.split(':')[0];
        sessionState.connectedUser = {
          id: creds.me.id,
          name: creds.me.name || 'Eximp and Cloves infrastructure ltd',
          phone: phone,
        };
      }
    } catch {}
  }

  return {
    status: sessionState.status,
    qrCode: sessionState.qrCode,
    user: sessionState.connectedUser,
    authExists: localExists,
    hasCloudinary: hasCloudinary,
  };
}

// ── Express API ──────────────────────────────────────────────────────────────

const app = express();
app.use(cors());
app.use(express.json());

app.get('/health', (req, res) => {
  res.json({ service: 'Eximp WhatsApp Gateway', status: 'online', gatewayStatus: sessionState.status });
});

app.get('/api/whatsapp/status', async (req, res) => {
  let status = getStatus();
  // Auto-connect in background if local auth exists but disconnected
  if (status.status === 'disconnected' && status.authExists && !sessionState.isInitializing) {
    console.log('[WhatsApp Gateway] Found existing credentials on status check; initiating auto-connect...');
    connectSocket().catch(e => console.warn('[WhatsApp Gateway] Auto-connect error:', e.message));
    status = getStatus();
  }
  res.json(status);
});

app.post('/api/whatsapp/connect', async (req, res) => {
  try {
    const status = await connectSocket();
    res.json(status);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/whatsapp/disconnect', async (req, res) => {
  try {
    const result = await disconnectSocket();
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/whatsapp/send', async (req, res) => {
  const { phone, message, mediaUrl } = req.body;
  if (!phone || !message) {
    return res.status(400).json({ error: 'Phone and message are required.' });
  }
  const result = await sendMessage(phone, message, mediaUrl);
  if (!result.success) {
    return res.status(400).json(result);
  }
  res.json(result);
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`[WhatsApp Gateway] Running on http://127.0.0.1:${PORT}`);
  // Auto-connect existing credentials immediately on boot
  if (hasLocalAuth()) {
    console.log('[WhatsApp Gateway] Found saved credentials; auto-connecting socket...');
    connectSocket().catch(e => console.warn('[WhatsApp Gateway] Boot auto-connect error:', e.message));
  } else {
    restoreAuthFromCloud().then((restored) => {
      if (restored) {
        console.log('[WhatsApp Gateway] Auto-connecting saved session from cloud...');
        connectSocket().catch(e => console.warn('[WhatsApp Gateway] Boot auto-connect error:', e.message));
      }
    });
  }
});
