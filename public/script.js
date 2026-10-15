(function () {

  // API CONFIGURATION
  

  const API_URL = 'http://127.0.0.1:3000/api/chat';
  const LEAD_API_URL = 'http://127.0.0.1:3000/api/lead';

  // DOM ELEMENTS


  const launcher = document.getElementById('hc-launcher');
  const panel = document.getElementById('hc-panel');
  const closeBtn = document.getElementById('hc-close');
  const messagesEl = document.getElementById('hc-messages');
  const input = document.getElementById('hc-input');
  const sendBtn = document.getElementById('hc-send');


  // CHAT STATE


  let history = [];
  let opened = false;

  // Prevent duplicate lead submissions
  const savedEmails = new Set();


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
        "Hi! I'm Honeycomb's assistant. Ask me about our services,portfolio,FAQs — or how to get in touch."
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

        appendMessage(
          'assistant',
          "Thanks! We've received your details. The Honeycomb team will get in touch with you."
        );

      } else {

        console.error(
          'Lead save failed:',
          data
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
          'Sorry, something went wrong. Please try again or email vani@honeycombindia.net.'
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
        "I couldn't connect just now. Please try again or reach us at +91 90352 90915."
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


  window.saveHoneycombLead = saveLead;


})();