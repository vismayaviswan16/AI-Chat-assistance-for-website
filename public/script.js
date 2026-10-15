(function () {

  // ====================================================================
  // >>> FILL IN: YOUR BACKEND URL <<<
  // While testing on your own computer, leave this as it is.
  // When you deploy the backend (server.py) online, replace it with
  // your server's address, e.g. 'https://chat.yourwebsite.com'
  // (no slash at the end).
  // ====================================================================
  const API_BASE = 'http://127.0.0.1:3000';

  // API CONFIGURATION (no need to edit these three lines)

  const API_URL = API_BASE + '/api/chat';
  const LEAD_API_URL = API_BASE + '/api/lead';
  const CONFIG_URL = API_BASE + '/api/config';

  // DOM ELEMENTS


  const launcher = document.getElementById('hc-launcher');
  const panel = document.getElementById('hc-panel');
  const closeBtn = document.getElementById('hc-close');
  const messagesEl = document.getElementById('hc-messages');
  const input = document.getElementById('hc-input');
  const sendBtn = document.getElementById('hc-send');
  const headerTitle = document.getElementById('hc-header-title');


  // CHAT STATE


  let history = [];
  let opened = false;

  // Prevent duplicate lead submissions
  const savedEmails = new Set();


  // ====================================================================
  // SITE CONFIG
  // Your company name, greeting and contact details are normally loaded
  // from company.json (edit that file, not this one).
  //
  // >>> OPTIONAL: FILL IN the fallback values below <<<
  // They are only shown if the backend can't be reached, so a visitor
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

    const parts = [
      siteConfig.contact_email,
      siteConfig.contact_phone
    ].filter(Boolean);

    return parts.length ? parts.join(' or ') : 'our team';
  }


  // ADD MESSAGE TO CHAT


  function appendMessage(role, text) {
    const el = document.createElement('div');

    el.className = 'hc-msg hc-msg-' + role;

    el.textContent = text;

    messagesEl.appendChild(el);

    messagesEl.scrollTop = messagesEl.scrollHeight;

    return el;
  }


  // OPEN / CLOSE CHAT

  function toggle() {
    panel.classList.toggle('hc-open');

    if (!opened) {
      opened = true;

      appendMessage(
        'assistant',
        siteConfig.greeting
      );
    }
  }


  launcher.addEventListener('click', toggle);
  closeBtn.addEventListener('click', toggle);


  // SAVE LEAD


  async function saveLead(email, name = '', interest = '') {

    if (!email) {
      console.log('No email provided.');
      return;
    }

    const normalizedEmail = email.toLowerCase().trim();

    // Prevent duplicate submissions
    if (savedEmails.has(normalizedEmail)) {
      console.log('Lead already saved:', email);
      return;
    }

    try {

      console.log('Saving lead:', {
        email,
        name,
        interest
      });

      const res = await fetch(LEAD_API_URL, {
        method: 'POST',

        headers: {
          'Content-Type': 'application/json'
        },

        body: JSON.stringify({
          email: email,
          name: name,
          interest: interest
        })
      });


      const data = await res.json();


      if (res.ok) {

        savedEmails.add(normalizedEmail);

        console.log(
          'Lead saved successfully:',
          data
        );

        // OPTIONAL: change this thank-you message to match your tone
        appendMessage(
          'assistant',
          "Thanks! We've received your details. Our team will get in touch with you."
        );

      } else {

        console.error(
          'Lead save failed:',
          data
        );

        appendMessage(
          'assistant',
          'Sorry, we could not save your details. Please contact ' + contactText() + '.'
        );

      }

    } catch (error) {

      console.error(
        'Could not save lead:',
        error
      );

    }
  }



  // SEND CHAT MESSAGE


  async function sendMessage() {

    const text = input.value.trim();

    if (!text) {
      return;
    }

    input.value = '';

    appendMessage(
      'user',
      text
    );


    history.push({
      role: 'user',
      content: text
    });


    const typingEl = appendMessage(
      'assistant',
      'Typing...'
    );

    typingEl.classList.add(
      'hc-msg-typing'
    );


    try {

      const res = await fetch(
        API_URL,
        {
          method: 'POST',

          headers: {
            'Content-Type': 'application/json'
          },

          body: JSON.stringify({
            message: text,
            history: history
          })
        }
      );


      const data = await res.json();

      typingEl.remove();


      if (data.reply) {

        appendMessage(
          'assistant',
          data.reply
        );


        history.push({
          role: 'assistant',
          content: data.reply
        });

      } else {

        appendMessage(
          'assistant',
          'Sorry, something went wrong. Please try again or contact ' + contactText() + '.'
        );

      }

    } catch (error) {

      console.error(
        'Chat error:',
        error
      );

      typingEl.remove();

      appendMessage(
        'assistant',
        "I couldn't connect just now. Please try again or contact " + contactText() + '.'
      );

    }
  }



  // SEND BUTTON


  sendBtn.addEventListener(
    'click',
    sendMessage
  );



  // ENTER KEY


  input.addEventListener(
    'keydown',
    function (event) {

      if (event.key === 'Enter') {
        sendMessage();
      }

    }
  );



  // MAKE SAVE LEAD AVAILABLE


  window.saveLead = saveLead;


})();