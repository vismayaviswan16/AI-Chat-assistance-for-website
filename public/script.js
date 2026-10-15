(function () {
  'use strict';

  // ====================================================================
  // >>> FILL IN: YOUR BACKEND URL <<<
  // While testing on your own computer, leave this as it is.
  // When you deploy the backend (server.py) online, replace it with
  // your server's address, e.g. 'https://chat.yourwebsite.com'
  // (no slash at the end).
  // ====================================================================
  const API_BASE = 'http://127.0.0.1:3000';

  // API CONFIGURATION (no need to edit these)
  const API_URL = API_BASE + '/api/chat';
  const CONFIG_URL = API_BASE + '/api/config';
  const REQUEST_TIMEOUT_MS = 120000; // give up on a reply after 2 minutes

  // DOM ELEMENTS
  const launcher = document.getElementById('hc-launcher');
  const panel = document.getElementById('hc-panel');
  const closeBtn = document.getElementById('hc-close');
  const messagesEl = document.getElementById('hc-messages');
  const input = document.getElementById('hc-input');
  const sendBtn = document.getElementById('hc-send');
  const headerTitle = document.getElementById('hc-header-title');

  if (!launcher || !panel || !closeBtn || !messagesEl || !input || !sendBtn) {
    console.error('Chat widget: required elements are missing from the page.');
    return;
  }

  // CHAT STATE
  // The conversation history is kept on the server. The browser only holds an
  // opaque session id that the server hands back with each reply.
  let sessionId = null;
  let greeted = false;
  let busy = false;

  // ====================================================================
  // SITE CONFIG
  // Your company name, greeting and contact details are normally loaded
  // from company.json (edit that file, not this one).
  //
  // >>> OPTIONAL: FILL IN the fallback values below <<<
  // They are only used if the backend can't be reached, so a visitor
  // still sees a way to contact you when the chatbot is offline.
  // ====================================================================
  let siteConfig = {
    company_name: '',                      // OPTIONAL: your company name
    greeting: 'Hi! How can I help you?',   // OPTIONAL: fallback greeting
    contact_email: '',                     // OPTIONAL: e.g. 'contact@yourcompany.com'
    contact_phone: ''                      // OPTIONAL: e.g. '+00 000 000 0000'
  };

  fetch(CONFIG_URL)
    .then(function (res) {
      return res.json();
    })
    .then(function (cfg) {
      siteConfig = Object.assign(siteConfig, cfg);
      if (headerTitle && siteConfig.company_name) {
        headerTitle.textContent = siteConfig.company_name;
      }
    })
    .catch(function (error) {
      console.log('Could not load site config, using defaults:', error);
    });

  // CONTACT TEXT USED IN ERROR MESSAGES
  function contactText() {
    const parts = [siteConfig.contact_email, siteConfig.contact_phone].filter(Boolean);
    return parts.length ? parts.join(' or ') : 'our team';
  }

  // TURN URLS AND EMAIL ADDRESSES INTO CLICKABLE LINKS
  // Built with DOM nodes (never innerHTML), so model output can't inject HTML.
  const LINK_RE = /(https?:\/\/[^\s<]+|[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})/g;

  function renderText(el, text) {
    el.textContent = '';
    let last = 0;
    let m;
    LINK_RE.lastIndex = 0;
    while ((m = LINK_RE.exec(text)) !== null) {
      let match = m[0];
      const trailing = match.match(/[.,;:!?)\]]+$/);
      const trail = trailing ? trailing[0] : '';
      if (trail) {
        match = match.slice(0, -trail.length);
      }
      if (!match) {
        continue;
      }
      if (m.index > last) {
        el.appendChild(document.createTextNode(text.slice(last, m.index)));
      }
      const a = document.createElement('a');
      a.textContent = match;
      a.href = /^https?:\/\//i.test(match) ? match : 'mailto:' + match;
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      el.appendChild(a);
      last = m.index + match.length;
      LINK_RE.lastIndex = last; // re-scan the trimmed punctuation as plain text
    }
    if (last < text.length) {
      el.appendChild(document.createTextNode(text.slice(last)));
    }
  }

  // ADD MESSAGE TO CHAT
  function appendMessage(role, text) {
    const el = document.createElement('div');
    el.className = 'hc-msg hc-msg-' + role;
    renderText(el, text);
    messagesEl.appendChild(el);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return el;
  }

  // OPEN / CLOSE CHAT
  function setOpen(open) {
    panel.classList.toggle('hc-open', open);
    launcher.setAttribute('aria-expanded', String(open));
    if (open) {
      if (!greeted) {
        greeted = true;
        appendMessage('assistant', siteConfig.greeting);
      }
      input.focus();
    } else {
      launcher.focus();
    }
  }

  function toggle() {
    setOpen(!panel.classList.contains('hc-open'));
  }

  launcher.addEventListener('click', toggle);
  closeBtn.addEventListener('click', function () {
    setOpen(false);
  });

  // ESC CLOSES THE PANEL
  panel.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      setOpen(false);
    }
  });

  function setBusy(value) {
    busy = value;
    sendBtn.disabled = value;
    panel.setAttribute('aria-busy', String(value));
  }

  // SEND CHAT MESSAGE
  async function sendMessage() {
    if (busy) {
      return;
    }
    const text = input.value.trim();
    if (!text) {
      return;
    }

    setBusy(true);
    input.value = '';
    appendMessage('user', text);

    const typingEl = appendMessage('assistant', 'Typing...');
    typingEl.classList.add('hc-msg-typing');

    const controller = new AbortController();
    const timer = setTimeout(function () {
      controller.abort();
    }, REQUEST_TIMEOUT_MS);

    try {
      const res = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: sessionId }),
        signal: controller.signal
      });

      let data = {};
      try {
        data = await res.json();
      } catch (parseError) {
        // non-JSON response: handled below as a generic error
      }

      typingEl.remove();

      if (data.session_id) {
        sessionId = data.session_id;
      }

      if (res.ok && data.reply) {
        appendMessage('assistant', data.reply);
      } else if ((res.status === 429 || res.status === 503) && data.error) {
        appendMessage('assistant', data.error);
      } else {
        appendMessage(
          'assistant',
          'Sorry, something went wrong. Please try again or contact ' + contactText() + '.'
        );
      }
    } catch (error) {
      console.error('Chat error:', error);
      typingEl.remove();
      appendMessage(
        'assistant',
        "I couldn't connect just now. Please try again or contact " + contactText() + '.'
      );
    } finally {
      clearTimeout(timer);
      setBusy(false);
      input.focus();
    }
  }

  // SEND BUTTON
  sendBtn.addEventListener('click', sendMessage);

  // ENTER KEY (ignored while an IME is composing, e.g. Japanese/Chinese input)
  input.addEventListener('keydown', function (event) {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      sendMessage();
    }
  });
})();
