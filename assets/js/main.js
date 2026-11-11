/* ==========================================================================
   Ela é simplesmente incrível — interações
   --------------------------------------------------------------------------
   Tudo em JavaScript puro (sem bibliotecas), organizado em módulos pequenos:

     CONFIG ........ número do WhatsApp, músicas e frases (edite aqui!)
     Util .......... funções de apoio
     Hearts ........ fundo com corações flutuando (canvas)
     Music ......... player usando a API oficial do YouTube
     Intro ......... abertura do "envelope" (o toque libera a música)
     Reveal ........ animações de entrada ao rolar a página
     Typed ......... frases sendo "digitadas" na capa
     Reasons ....... cartas que viram
     Slideshow ..... fotos passando sozinhas (estilo stories)
     Lightbox ...... galeria ampliada com swipe e teclado
     RingVideo ..... o vídeo do anel só toca quando aparece na tela
     Kiss .......... o final: "Quero" / "Não quero" → WhatsApp
     TapHearts ..... coraçõezinhos onde ela tocar
   ========================================================================== */

(() => {
  "use strict";

  /* ------------------------------------------------------------------------
     CONFIG — é só mexer aqui para personalizar
     ------------------------------------------------------------------------ */
  const CONFIG = {
    // Número do Lucas com DDI 55 + DDD + número, só dígitos. Ex.: "5531999999999"
    whatsapp: "553185073624",

    // Mensagens que chegam no WhatsApp do Lucas
    messages: {
      yes: "Lucas, eu vi o site… e QUERO meu beijo! 💋💗",
      no: "Lucas, eu cliquei em \"Não quero\" 🙈 (mas você sabe que é mentira 😏💋)",
    },

    // Músicas (IDs de vídeos oficiais do YouTube). A primeira toca ao abrir.
    playlist: [
      { id: "lp-EO5I60KA", title: "Thinking Out Loud · Ed Sheeran" },
      { id: "F-cO2CMue4Q", title: "It's You · Ali Gatie" },
      { id: "nSDgHBxUbVQ", title: "Photograph · Ed Sheeran" },
    ],

    // Frases da capa
    typed: [
      "Você é a coisa mais bonita que já me aconteceu.",
      "Meu sorriso tem o seu nome.",
      "Obrigado por existir do jeitinho que você é.",
      "Eu te amo. Muito. Demais.",
    ],

    slideDuration: 5000, // tempo de cada foto no slideshow (ms)
  };

  /* ------------------------------------------------------------------------
     Util
     ------------------------------------------------------------------------ */
  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const isTouch = window.matchMedia("(hover: none)").matches;
  const rand = (min, max) => Math.random() * (max - min) + min;
  const HEART_PATH =
    "M16 28.6s-11.4-7-11.4-15.1A6.6 6.6 0 0 1 16 9.2a6.6 6.6 0 0 1 11.4 4.3C27.4 21.6 16 28.6 16 28.6z";

  /** Solta corações a partir de um ponto da tela (x, y). */
  function burstHearts(x, y, amount = 10, spread = 120) {
    if (reducedMotion) return;
    const colors = ["#ff6ea0", "#ff9cbf", "#ffc0d6", "#ff4d8a", "#fff4f8"];
    for (let i = 0; i < amount; i++) {
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("viewBox", "0 0 32 32");
      svg.setAttribute("aria-hidden", "true");
      svg.classList.add("burst-heart");
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", HEART_PATH);
      svg.appendChild(path);
      const angle = rand(0, Math.PI * 2);
      const dist = rand(spread * 0.4, spread);
      svg.style.left = `${x}px`;
      svg.style.top = `${y}px`;
      svg.style.setProperty("--s", `${rand(12, 28)}px`);
      svg.style.setProperty("--c", colors[i % colors.length]);
      svg.style.setProperty("--dx", `${Math.cos(angle) * dist}px`);
      svg.style.setProperty("--dy", `${Math.sin(angle) * dist - spread * 0.5}px`);
      svg.style.setProperty("--rot", `${rand(-60, 60)}deg`);
      document.body.appendChild(svg);
      svg.addEventListener("animationend", () => svg.remove(), { once: true });
    }
  }

  /* ------------------------------------------------------------------------
     Hearts — corações subindo devagar no fundo
     ------------------------------------------------------------------------ */
  const Hearts = (() => {
    const canvas = $("#hearts-canvas");
    if (!canvas || reducedMotion) return { start() {} };
    const ctx = canvas.getContext("2d");
    const heart = new Path2D(HEART_PATH);
    let w = 0, h = 0, dpr = 1, items = [], running = false, last = 0;

    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const target = Math.round(Math.min(34, (w * h) / 32000));
      while (items.length < target) items.push(make(true));
      items.length = target;
    }

    function make(anywhere = false) {
      return {
        x: rand(0, w),
        y: anywhere ? rand(0, h) : h + 30,
        s: rand(0.35, 1.1),
        vy: rand(12, 34),
        sway: rand(0.4, 1.4),
        phase: rand(0, Math.PI * 2),
        a: rand(0.08, 0.32),
        rot: rand(-0.4, 0.4),
      };
    }

    function tick(t) {
      if (!running) return;
      const dt = Math.min((t - last) / 1000, 0.05);
      last = t;
      ctx.clearRect(0, 0, w, h);
      for (const p of items) {
        p.y -= p.vy * dt;
        p.phase += dt * p.sway;
        if (p.y < -40) Object.assign(p, make());
        ctx.save();
        ctx.translate(p.x + Math.sin(p.phase) * 18, p.y);
        ctx.rotate(p.rot + Math.sin(p.phase) * 0.2);
        ctx.scale(p.s, p.s);
        ctx.translate(-16, -16);
        ctx.globalAlpha = p.a;
        ctx.fillStyle = "#ff6ea0";
        ctx.fill(heart);
        ctx.restore();
      }
      requestAnimationFrame(tick);
    }

    function start() {
      if (running) return;
      running = true;
      last = performance.now();
      requestAnimationFrame(tick);
    }

    window.addEventListener("resize", resize, { passive: true });
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) running = false;
      else start();
    });
    resize();
    return { start };
  })();

  /* ------------------------------------------------------------------------
     Music — YouTube IFrame API (o áudio vem dos vídeos oficiais)
     ------------------------------------------------------------------------ */
  const Music = (() => {
    const ui = $("#player");
    const toggle = $("#player-toggle");
    const next = $("#player-next");
    const songLabel = $("#player-song");
    const label = $("#player-label");
    let player = null;
    let ready = false;
    let wantPlay = false;
    let index = 0;

    function setPlaying(on) {
      ui.classList.toggle("is-playing", on);
      toggle.setAttribute("aria-pressed", String(on));
      toggle.setAttribute("aria-label", on ? "Pausar música" : "Tocar música");
      label.textContent = on ? "Tocando pra você" : "Toque pra ouvir";
    }

    function setSong(i) {
      index = (i + CONFIG.playlist.length) % CONFIG.playlist.length;
      songLabel.textContent = CONFIG.playlist[index].title;
    }

    function load() {
      // a API chama window.onYouTubeIframeAPIReady quando estiver pronta
      window.onYouTubeIframeAPIReady = () => {
        player = new window.YT.Player("yt-player", {
          host: "https://www.youtube-nocookie.com",
          width: 200,
          height: 200,
          videoId: CONFIG.playlist[0].id,
          playerVars: { autoplay: 0, controls: 0, disablekb: 1, playsinline: 1, rel: 0, fs: 0, iv_load_policy: 3 },
          events: {
            onReady: () => {
              ready = true;
              player.setVolume(85);
              if (wantPlay) player.playVideo();
            },
            onStateChange: (e) => {
              const S = window.YT.PlayerState;
              if (e.data === S.PLAYING) setPlaying(true);
              else if (e.data === S.PAUSED) setPlaying(false);
              else if (e.data === S.ENDED) change(index + 1);
            },
            onError: () => change(index + 1), // vídeo indisponível? pula pro próximo
          },
        });
      };
      const tag = document.createElement("script");
      tag.src = "https://www.youtube.com/iframe_api";
      tag.async = true;
      document.head.appendChild(tag);
    }

    function play() {
      wantPlay = true;
      if (ready) player.playVideo();
    }

    function pause() {
      wantPlay = false;
      if (ready) player.pauseVideo();
      setPlaying(false);
    }

    function change(i) {
      setSong(i);
      if (ready) {
        player.loadVideoById(CONFIG.playlist[index].id);
        wantPlay = true;
      }
    }

    function show() { ui.classList.add("is-visible"); }

    toggle.addEventListener("click", () => (ui.classList.contains("is-playing") ? pause() : play()));
    next.addEventListener("click", () => change(index + 1));
    setSong(0);

    return { load, play, show };
  })();

  /* ------------------------------------------------------------------------
     Intro — o envelope
     ------------------------------------------------------------------------ */
  const Intro = (() => {
    const intro = $("#intro");
    const openBtn = $("#intro-open");
    const silentBtn = $("#intro-silent");

    function open(withMusic) {
      // tocar dentro do clique: é o que permite som no celular (iOS/Android)
      if (withMusic) Music.play();
      intro.classList.add("is-opening");
      if (!reducedMotion) {
        const r = openBtn.getBoundingClientRect();
        burstHearts(r.left + r.width / 2, r.top + r.height / 2, 16, 160);
      }
      setTimeout(() => {
        intro.classList.add("is-hidden");
        document.body.classList.remove("is-locked");
        Music.show();
        Typed.start();
      }, reducedMotion ? 50 : 1300);
      setTimeout(() => intro.remove(), 2600);
    }

    openBtn.addEventListener("click", () => open(true), { once: true });
    silentBtn.addEventListener("click", () => open(false), { once: true });
    openBtn.focus({ preventScroll: true });
  })();

  /* ------------------------------------------------------------------------
     Reveal — elementos surgem suavemente ao entrar na tela
     ------------------------------------------------------------------------ */
  (() => {
    const els = $$(".reveal");
    if (!("IntersectionObserver" in window) || reducedMotion) {
      els.forEach((el) => el.classList.add("is-visible"));
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -6% 0px" }
    );
    els.forEach((el) => io.observe(el));
  })();

  /* ------------------------------------------------------------------------
     Typed — efeito de digitação
     ------------------------------------------------------------------------ */
  const Typed = (() => {
    const el = $("#typed");
    let started = false;

    async function loop() {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      let i = 0;
      for (;;) {
        const text = CONFIG.typed[i % CONFIG.typed.length];
        for (let c = 1; c <= text.length; c++) {
          el.textContent = text.slice(0, c);
          await wait(reducedMotion ? 0 : 45);
        }
        await wait(2600);
        for (let c = text.length; c >= 0; c--) {
          el.textContent = text.slice(0, c);
          await wait(reducedMotion ? 0 : 22);
        }
        await wait(350);
        i++;
      }
    }

    return {
      start() {
        if (started || !el) return;
        started = true;
        loop();
      },
    };
  })();

  /* ------------------------------------------------------------------------
     Reasons — cartas que viram ao toque
     ------------------------------------------------------------------------ */
  $$(".flip").forEach((card) => {
    card.addEventListener("click", (e) => {
      const on = card.classList.toggle("is-flipped");
      card.setAttribute("aria-pressed", String(on));
      if (on) burstHearts(e.clientX || card.getBoundingClientRect().left + 40, e.clientY || card.getBoundingClientRect().top + 40, 6, 70);
    });
  });

  /* ------------------------------------------------------------------------
     Dados das fotos (lidos da galeria, que já está no HTML)
     ------------------------------------------------------------------------ */
  const photos = $$(".gallery__btn").map((btn) => {
    const img = $("img", btn);
    return {
      btn,
      full: btn.dataset.full,
      small: img.getAttribute("src"),
      alt: img.alt,
      caption: btn.dataset.caption,
    };
  });

  /* ------------------------------------------------------------------------
     Slideshow — as fotos passando sozinhas, como stories
     ------------------------------------------------------------------------ */
  (() => {
    const stage = $("#slideshow");
    const slidesBox = $("#show-slides");
    const caption = $("#show-caption");
    const progress = $("#show-progress");
    if (!stage || !photos.length) return;

    const slides = photos.map((p, i) => {
      const slide = document.createElement("div");
      slide.className = "show__slide";
      const img = document.createElement("img");
      img.alt = p.alt;
      img.decoding = "async";
      img.dataset.src = p.full; // carregada sob demanda (só quando chega a vez)
      slide.appendChild(img);
      slidesBox.appendChild(slide);
      const bar = document.createElement("span");
      bar.appendChild(document.createElement("i"));
      progress.appendChild(bar);
      return { slide, img, bar };
    });
    stage.style.setProperty("--dur", `${CONFIG.slideDuration}ms`);

    let current = -1;
    let timer = null;
    let visible = false;
    let paused = false;

    function ensureLoaded(i) {
      const s = slides[(i + slides.length) % slides.length];
      if (!s.img.src) s.img.src = s.img.dataset.src;
    }

    function go(i) {
      i = (i + slides.length) % slides.length;
      if (current >= 0) slides[current].slide.classList.remove("is-active");
      slides.forEach((s, k) => {
        s.bar.classList.toggle("is-done", k < i);
        s.bar.classList.remove("is-active");
      });
      current = i;
      ensureLoaded(i);
      ensureLoaded(i + 1);
      const s = slides[i];
      s.slide.classList.add("is-active");
      void s.bar.offsetWidth; // reinicia a animação da barrinha
      s.bar.classList.add("is-active");
      caption.textContent = photos[i].caption;
      schedule();
    }

    function schedule() {
      clearTimeout(timer);
      if (visible && !paused) timer = setTimeout(() => go(current + 1), CONFIG.slideDuration);
    }

    function setPaused(p) {
      paused = p;
      stage.classList.toggle("is-paused", p || !visible);
      if (p) clearTimeout(timer);
      else go(current); // retoma a foto atual do começo
    }

    $("#show-prev").addEventListener("click", () => go(current - 1));
    $("#show-next").addEventListener("click", () => go(current + 1));

    // Swipe no celular
    let startX = null;
    stage.addEventListener("touchstart", (e) => { startX = e.touches[0].clientX; }, { passive: true });
    stage.addEventListener("touchend", (e) => {
      if (startX === null) return;
      const dx = e.changedTouches[0].clientX - startX;
      if (Math.abs(dx) > 40) go(current + (dx < 0 ? 1 : -1));
      startX = null;
    });

    // Pausa quando o mouse está em cima (no computador)
    if (!isTouch) {
      stage.addEventListener("mouseenter", () => setPaused(true));
      stage.addEventListener("mouseleave", () => setPaused(false));
    }

    // Só roda quando está visível na tela (economiza bateria)
    const io = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      stage.classList.toggle("is-paused", !visible);
      if (visible) go(current < 0 ? 0 : current);
      else clearTimeout(timer);
    }, { threshold: 0.35 });
    io.observe(stage);
  })();

  /* ------------------------------------------------------------------------
     Lightbox — foto ampliada
     ------------------------------------------------------------------------ */
  (() => {
    const box = $("#lightbox");
    const img = $("#lb-img");
    const cap = $("#lb-caption");
    const count = $("#lb-count");
    let index = 0;
    let lastFocus = null;

    function show(i) {
      index = (i + photos.length) % photos.length;
      const p = photos[index];
      img.style.animation = "none";
      void img.offsetWidth;
      img.style.animation = "";
      img.src = p.full;
      img.alt = p.alt;
      cap.textContent = p.caption;
      count.textContent = `${index + 1} / ${photos.length}`;
      // pré-carrega as vizinhas para o swipe ficar instantâneo
      [index + 1, index - 1].forEach((k) => {
        const pre = new Image();
        pre.src = photos[(k + photos.length) % photos.length].full;
      });
    }

    function open(i) {
      lastFocus = document.activeElement;
      show(i);
      box.hidden = false;
      document.body.style.overflow = "hidden";
      $("#lb-close").focus();
    }

    function close() {
      box.hidden = true;
      document.body.style.overflow = "";
      lastFocus?.focus();
    }

    photos.forEach((p, i) => p.btn.addEventListener("click", () => open(i)));
    $("#lb-close").addEventListener("click", close);
    $("#lb-prev").addEventListener("click", () => show(index - 1));
    $("#lb-next").addEventListener("click", () => show(index + 1));
    box.addEventListener("click", (e) => { if (e.target === box) close(); });

    document.addEventListener("keydown", (e) => {
      if (box.hidden) return;
      if (e.key === "Escape") close();
      if (e.key === "ArrowRight") show(index + 1);
      if (e.key === "ArrowLeft") show(index - 1);
      if (e.key === "Tab") {
        // mantém o foco dentro do lightbox
        const f = $$("button", box);
        const first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });

    let startX = null;
    box.addEventListener("touchstart", (e) => { startX = e.touches[0].clientX; }, { passive: true });
    box.addEventListener("touchend", (e) => {
      if (startX === null) return;
      const dx = e.changedTouches[0].clientX - startX;
      if (Math.abs(dx) > 40) show(index + (dx < 0 ? 1 : -1));
      startX = null;
    });
  })();

  /* ------------------------------------------------------------------------
     RingVideo — toca o anel só quando ele está na tela
     ------------------------------------------------------------------------ */
  (() => {
    const video = $("#ring-video");
    if (!video) return;
    if (reducedMotion) return; // fica o pôster parado
    const io = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        if (video.preload !== "auto") { video.preload = "auto"; video.load(); }
        video.play().catch(() => {});
      } else {
        video.pause();
      }
    }, { threshold: 0.25, rootMargin: "200px 0px" });
    io.observe(video);
  })();

  /* ------------------------------------------------------------------------
     Kiss — o final
     ------------------------------------------------------------------------ */
  (() => {
    const yes = $("#kiss-yes");
    const no = $("#kiss-no");
    const area = $("#kiss-actions");
    const feedback = $("#kiss-feedback");
    if (!yes || !no) return;

    const teases = ["Tem certeza? 🥺", "Pensa bem… 😳", "Última chance, hein! 😏"];
    let dodges = 0;

    function whatsappUrl(text) {
      const number = CONFIG.whatsapp.replace(/\D/g, "");
      const base = number ? `https://wa.me/${number}` : "https://wa.me/";
      return `${base}?text=${encodeURIComponent(text)}`;
    }

    function send(text) {
      const url = whatsappUrl(text);
      // abre direto no clique (não é bloqueado como pop-up)
      const win = window.open(url, "_blank");
      if (win) win.opener = null;
      else window.location.href = url;
    }

    function dodge() {
      if (dodges >= teases.length) return false;
      const a = area.getBoundingClientRect();
      const b = no.getBoundingClientRect();
      const maxX = Math.max(0, (a.width - b.width) / 2);
      const x = rand(-maxX, maxX);
      const y = rand(-40, 40);
      no.style.transform = `translate(${x}px, ${y}px) rotate(${rand(-8, 8)}deg)`;
      feedback.textContent = teases[dodges];
      dodges++;
      if (dodges === teases.length) {
        setTimeout(() => {
          no.style.transform = "";
          feedback.textContent = "Tá bom, tá bom… pode clicar 🙈";
        }, 700);
      }
      return true;
    }

    yes.addEventListener("click", () => {
      const r = yes.getBoundingClientRect();
      burstHearts(r.left + r.width / 2, r.top + r.height / 2, 34, 260);
      feedback.textContent = "Eba! Indo pro WhatsApp buscar seu beijo… 💋";
      send(CONFIG.messages.yes);
    });

    // no computador ele foge quando o mouse chega perto
    if (!isTouch) no.addEventListener("mouseenter", dodge);

    no.addEventListener("click", (e) => {
      if (dodge()) { e.preventDefault(); return; }
      feedback.textContent = "Hmm… vou fingir que acredito 😏";
      send(CONFIG.messages.no);
    });
  })();

  /* ------------------------------------------------------------------------
     TapHearts — coraçõezinhos onde ela tocar
     ------------------------------------------------------------------------ */
  document.addEventListener("pointerdown", (e) => {
    if (document.body.classList.contains("is-locked")) return;
    if (e.target.closest("button, a, .lightbox, .player")) return;
    burstHearts(e.clientX, e.clientY, 5, 60);
  });

  /* ------------------------------------------------------------------------
     Início
     ------------------------------------------------------------------------ */
  const year = $("#year");
  if (year) year.textContent = String(new Date().getFullYear());
  Hearts.start();
  Music.load();
})();
