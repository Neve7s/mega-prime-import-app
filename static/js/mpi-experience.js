/**
 * MEGA PRIME IMPORT LGM (Ecuador) — Interactive 3D & GSAP Experience Engine
 * Optimizado para 60 FPS en Mobile y Desktop:
 * - Pausa automática de WebGL (Three.js) fuera del viewport con IntersectionObserver
 * - Animaciones bidireccionales (scroll bajada y subida) con GSAP ScrollTrigger
 * - Separación de carga gráfica Mobile vs Desktop con gsap.matchMedia()
 * - Respeto total a prefers-reduced-motion y soporte HTMX (htmx:afterSwap)
 */
(function () {
  "use strict";

  var prefersReducedMotion =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  document.documentElement.classList.add("js-mpi-ready");

  // ─────────────────────────────────────────────────────────────
  // 1. MOTOR 3D THREE.JS (HERO ARQUITECTÓNICO INTERACTIVO)
  // ─────────────────────────────────────────────────────────────
  function initHero3D() {
    var canvas = document.getElementById("mpi-hero-3d");
    if (!canvas || typeof window.THREE === "undefined" || prefersReducedMotion) {
      return;
    }

    var THREE = window.THREE;
    var container = canvas.parentElement;
    if (!container) return;

    var isMobile = window.innerWidth < 768;
    var renderer;
    try {
      renderer = new THREE.WebGLRenderer({
        canvas: canvas,
        alpha: true,
        antialias: !isMobile,
        powerPreference: "high-performance",
      });
    } catch (err) {
      // Si el dispositivo no soporta WebGL, degradación silenciosa sin errores.
      return;
    }

    var maxDpr = isMobile ? 1.0 : 1.5;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, maxDpr));

    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(
      38,
      container.clientWidth / Math.max(container.clientHeight, 1),
      0.1,
      100
    );
    camera.position.set(0, 1.2, isMobile ? 11.5 : 9.2);

    // Iluminación arquitectónica cálida (Dorado #D4AF37 + Luz fría técnica)
    var ambientLight = new THREE.AmbientLight(0xffffff, 0.55);
    scene.add(ambientLight);

    var goldLight = new THREE.PointLight(0xd4af37, 2.4, 24);
    goldLight.position.set(4.5, 4.0, 5.0);
    scene.add(goldLight);

    var rimLight = new THREE.DirectionalLight(0xf4dc94, 1.15);
    rimLight.position.set(-5.0, 3.0, 3.5);
    scene.add(rimLight);

    var coolFill = new THREE.PointLight(0x3b82f6, 0.65, 18);
    coolFill.position.set(-4.0, -3.5, 2.0);
    scene.add(coolFill);

    // Grupo principal que representa las líneas de importación en Ecuador
    var rootGroup = new THREE.Group();
    scene.add(rootGroup);

    // Materiales compartidos (reutilizados para minimizar draw calls y memoria GPU)
    var matGoldWire = new THREE.MeshBasicMaterial({
      color: 0xd4af37,
      wireframe: true,
      transparent: true,
      opacity: 0.22,
    });

    var matGraphiteSlab = new THREE.MeshStandardMaterial({
      color: 0x161618,
      metalness: 0.55,
      roughness: 0.28,
      transparent: true,
      opacity: 0.88,
    });

    var matGoldAccent = new THREE.MeshStandardMaterial({
      color: 0xd4af37,
      metalness: 0.78,
      roughness: 0.22,
    });

    var matWpcWood = new THREE.MeshStandardMaterial({
      color: 0x8c5828,
      metalness: 0.2,
      roughness: 0.45,
    });

    // A) Onda Modular de Cubierta / Teja Roma & Española (arriba-izquierda / centro)
    var waveGroup = new THREE.Group();
    var ribCount = isMobile ? 7 : 12;
    var ribGeo = new THREE.BoxGeometry(0.32, 0.12, 3.6);
    var edgeGoldGeo = new THREE.BoxGeometry(0.05, 0.14, 3.62);

    for (var i = 0; i < ribCount; i++) {
      var offset = (i - (ribCount - 1) / 2) * 0.46;
      var archY = Math.sin(i * 0.85) * 0.22;
      var rib = new THREE.Mesh(
        ribGeo,
        i % 3 === 0 ? matWpcWood : matGraphiteSlab
      );
      rib.position.set(offset, archY, 0);
      rib.rotation.z = Math.cos(i * 0.85) * 0.18;
      rib.userData = { baseY: archY, index: i };
      waveGroup.add(rib);

      if (i % 2 === 0) {
        var goldStrip = new THREE.Mesh(edgeGoldGeo, matGoldAccent);
        goldStrip.position.set(offset + 0.16, archY + 0.02, 0);
        goldStrip.userData = { baseY: archY + 0.02, index: i };
        waveGroup.add(goldStrip);
      }
    }
    waveGroup.position.set(-1.4, 0.35, -0.8);
    waveGroup.rotation.set(0.42, -0.38, 0.12);
    rootGroup.add(waveGroup);

    // B) Placas Arquitectónicas en Capas (Pisos SPC / Porcelanato / Policarbonato)
    var slabGroup = new THREE.Group();
    var slabGeo = new THREE.BoxGeometry(2.8, 0.08, 1.9);
    for (var s = 0; s < 3; s++) {
      var slab = new THREE.Mesh(
        slabGeo,
        s === 1 ? matGoldWire : matGraphiteSlab
      );
      slab.position.set(0, s * 0.34 - 0.34, 0);
      slab.userData = { layerIndex: s, baseY: s * 0.34 - 0.34 };
      slabGroup.add(slab);
    }
    slabGroup.position.set(1.8, -0.65, -0.4);
    slabGroup.rotation.set(0.35, -0.52, -0.08);
    rootGroup.add(slabGroup);

    // C) Grilla de Nivelación Láser 4D (Herrajes y Precisión)
    var gridHelper = new THREE.GridHelper(
      14,
      isMobile ? 12 : 20,
      0xd4af37,
      0x2a2925
    );
    gridHelper.position.y = -2.3;
    if (gridHelper.material) {
      gridHelper.material.transparent = true;
      gridHelper.material.opacity = 0.24;
    }
    rootGroup.add(gridHelper);

    // Estado de interacción (puntero + scroll)
    var targetRotX = 0;
    var targetRotY = 0;
    var currentRotX = 0;
    var currentRotY = 0;
    var scrollProgress = 0;
    var activeProfileBoost = 1;

    if (!isMobile) {
      window.addEventListener(
        "mousemove",
        function (e) {
          var nx = (e.clientX / window.innerWidth) * 2 - 1;
          var ny = (e.clientY / window.innerHeight) * 2 - 1;
          targetRotY = nx * 0.28;
          targetRotX = ny * 0.16;
        },
        { passive: true }
      );
    }

    window.addEventListener(
      "scroll",
      function () {
        var maxScroll = Math.max(window.innerHeight, 600);
        scrollProgress = Math.min(Math.max(window.scrollY / maxScroll, 0), 1.5);
      },
      { passive: true }
    );

    // API pública para que los botones del Hero/Pilares interactúen con el 3D
    window.MpiHero3D = {
      pulseProfile: function (mode) {
        activeProfileBoost = mode === "tejas" ? 1.65 : mode === "wpc" ? 1.35 : 1.15;
        targetRotY += 0.35;
      },
    };

    function onResize() {
      if (!container) return;
      var w = container.clientWidth || window.innerWidth;
      var h = container.clientHeight || 600;
      camera.aspect = w / Math.max(h, 1);
      camera.updateProjectionMatrix();
      renderer.setSize(w, h, false);
    }
    onResize();

    var resizeTimer = null;
    window.addEventListener(
      "resize",
      function () {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(onResize, 120);
      },
      { passive: true }
    );

    // Control de bucle para CERO LAG fuera del viewport
    var isRunning = false;
    var rafId = null;
    var clock = new THREE.Clock();

    function renderLoop() {
      if (!isRunning) return;
      rafId = requestAnimationFrame(renderLoop);

      var t = clock.getElapsedTime();

      currentRotX += (targetRotX - currentRotX) * 0.06;
      currentRotY += (targetRotY - currentRotY) * 0.06;

      // Rotación combinada: tiempo + puntero + scroll bidireccional
      rootGroup.rotation.y = currentRotY + t * 0.07 + scrollProgress * 0.55;
      rootGroup.rotation.x = currentRotX + scrollProgress * 0.25;
      rootGroup.position.y = -scrollProgress * 0.9;

      // Movimiento ondulatorio didáctico de los perfiles/tejas
      var children = waveGroup.children;
      for (var c = 0; c < children.length; c++) {
        var mesh = children[c];
        var idx = mesh.userData.index || 0;
        mesh.position.y =
          mesh.userData.baseY +
          Math.sin(t * 1.6 + idx * 0.55) * 0.09 * activeProfileBoost;
      }

      // Despiece vertical de las capas al hacer scroll (efecto Exploded View)
      var slabs = slabGroup.children;
      for (var k = 0; k < slabs.length; k++) {
        var sMesh = slabs[k];
        var lIdx = sMesh.userData.layerIndex || 0;
        var spread = 1 + scrollProgress * 0.85 + Math.sin(t * 1.2) * 0.12;
        sMesh.position.y = (lIdx - 1) * 0.36 * spread;
      }

      renderer.render(scene, camera);
    }

    function startLoop() {
      if (!isRunning) {
        isRunning = true;
        clock.start();
        renderLoop();
      }
    }

    function stopLoop() {
      isRunning = false;
      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
    }

    if ("IntersectionObserver" in window) {
      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              startLoop();
            } else {
              stopLoop();
            }
          });
        },
        { threshold: 0.02 }
      );
      observer.observe(container);
    } else {
      startLoop();
    }

    document.addEventListener("visibilitychange", function () {
      if (document.hidden) {
        stopLoop();
      } else {
        startLoop();
      }
    });
  }

  // ─────────────────────────────────────────────────────────────
  // 2. GSAP + SCROLLTRIGGER: PARALLAX BIDIRECCIONAL & TÍTULOS
  // ─────────────────────────────────────────────────────────────
  function initScrollAnimations() {
    if (
      typeof window.gsap === "undefined" ||
      typeof window.ScrollTrigger === "undefined" ||
      prefersReducedMotion
    ) {
      return;
    }

    var gsap = window.gsap;
    var ScrollTrigger = window.ScrollTrigger;
    gsap.registerPlugin(ScrollTrigger);
    gsap.config({ force3D: true, nullTargetWarn: false });

    // 2.1 Barra superior de progreso de scroll
    var progressBar = document.getElementById("mpi-scroll-progress");
    if (progressBar) {
      gsap.to(progressBar, {
        scaleX: 1,
        ease: "none",
        scrollTrigger: {
          trigger: document.documentElement,
          start: "top top",
          end: "bottom bottom",
          scrub: 0.15,
        },
      });
    }

    // 2.2 Títulos con revelación cinemática + línea láser dorada (bajada y subida)
    var titles = gsap.utils.toArray('[data-animate="title"]');
    titles.forEach(function (titleEl) {
      gsap.fromTo(
        titleEl,
        { y: 32, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.75,
          ease: "power3.out",
          scrollTrigger: {
            trigger: titleEl,
            start: "top 88%",
            end: "bottom 12%",
            toggleActions: "play reverse play reverse",
          },
        }
      );
    });

    var laserLines = gsap.utils.toArray("[data-laser-line]");
    laserLines.forEach(function (lineEl) {
      gsap.fromTo(
        lineEl,
        { scaleX: 0, transformOrigin: "left center" },
        {
          scaleX: 1,
          duration: 0.85,
          ease: "expo.out",
          scrollTrigger: {
            trigger: lineEl,
            start: "top 90%",
            end: "bottom 10%",
            toggleActions: "play reverse play reverse",
          },
        }
      );
    });

    // 2.3 Grupos escalonados (tarjetas de pilares, ventajas, sellos, testimonios, catálogo)
    var staggerGroups = gsap.utils.toArray("[data-stagger-group]");
    staggerGroups.forEach(function (groupEl) {
      var items = groupEl.querySelectorAll("[data-stagger-item]");
      if (!items.length) return;
      gsap.fromTo(
        items,
        { y: 36, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.65,
          stagger: 0.1,
          ease: "power2.out",
          scrollTrigger: {
            trigger: groupEl,
            start: "top 86%",
            end: "bottom 14%",
            toggleActions: "play reverse play reverse",
          },
        }
      );
    });

    // 2.4 Línea de tiempo de Importación Directa Ecuador (Sección Ventajas)
    var importProgress = document.querySelector("[data-import-progress]");
    var importContainer = document.querySelector("[data-import-timeline]");
    if (importProgress && importContainer) {
      gsap.fromTo(
        importProgress,
        { scaleY: 0, transformOrigin: "top center" },
        {
          scaleY: 1,
          ease: "none",
          scrollTrigger: {
            trigger: importContainer,
            start: "top 75%",
            end: "bottom 35%",
            scrub: 0.5,
          },
        }
      );
    }

    // 2.5 Parallax Bidireccional adaptado por dispositivo con gsap.matchMedia()
    var mm = gsap.matchMedia();

    mm.add(
      {
        isDesktop: "(min-width: 1024px)",
        isMobile: "(max-width: 1023px)",
      },
      function (context) {
        var factor = context.conditions.isDesktop ? 1 : 0.45;
        var parallaxItems = gsap.utils.toArray("[data-parallax]");

        parallaxItems.forEach(function (el) {
          var rawSpeed = parseFloat(el.getAttribute("data-parallax") || "24");
          var distance = rawSpeed * factor;

          gsap.fromTo(
            el,
            { y: -distance * 0.5 },
            {
              y: distance,
              ease: "none",
              scrollTrigger: {
                trigger: el,
                start: "top bottom",
                end: "bottom top",
                scrub: context.conditions.isDesktop ? 0.6 : 0.35,
              },
            }
          );
        });
      }
    );

    // 2.6 Contadores numéricos didácticos
    var counters = gsap.utils.toArray("[data-counter]");
    counters.forEach(function (counterEl) {
      var targetVal = parseFloat(counterEl.getAttribute("data-counter") || "0");
      var prefix = counterEl.getAttribute("data-prefix") || "";
      var suffix = counterEl.getAttribute("data-suffix") || "";
      if (!targetVal) return;

      var proxy = { val: 0 };
      ScrollTrigger.create({
        trigger: counterEl,
        start: "top 90%",
        onEnter: function () {
          gsap.to(proxy, {
            val: targetVal,
            duration: 1.4,
            ease: "power2.out",
            onUpdate: function () {
              var formatted =
                targetVal >= 1000
                  ? Math.round(proxy.val).toLocaleString("en-US")
                  : Math.round(proxy.val);
              counterEl.textContent = prefix + formatted + suffix;
            },
          });
        },
      });
    });
  }

  // ─────────────────────────────────────────────────────────────
  // 3. EXPLORADOR DIDÁCTICO DE MATERIALES ("ANATOMÍA TÉCNICA")
  // ─────────────────────────────────────────────────────────────
  var DIDACTIC_MATERIALS = {
    tejas: {
      badge: "Cubiertas Termoacústicas Importadas",
      title: "Teja PVC / ASA (Perfiles Roma, Española y Trapezoidal)",
      subtitle:
        "Diseñada para soportar la radiación UV ecuatorial de la Sierra y la humedad salina de la Costa sin oxidarse ni decolorarse.",
      saving: "-6°C a -8°C temperatura interior",
      lifespan: "25+ años vida útil",
      norm: "Espesor 2.5 mm / 2.2 mm · Ignífuga Clase B1",
      link: "/catalogo/?categoria=tejas-y-cubiertas",
      linkLabel: "Explorar Tejas Roma, Española y Trapezoidal",
      layers: [
        {
          step: "Capa 01 · Blindaje Exterior",
          name: "Resina Acrílica ASA Ultra-UV",
          desc: "Reflectancia solar superior que bloquea la degradación UV en Quito, Ambato y Cuenca y mantiene el color intacto (Terracota, Negro, Verde, Azul).",
          color: "#D4AF37",
        },
        {
          step: "Capa 02 · Núcleo Central",
          name: "UPVC Espumado Termoacústico",
          desc: "Aísla hasta un 35% el ruido de lluvias torrenciales y granizo, evitando el efecto tambor de los techos metálicos tradicionales.",
          color: "#161617",
        },
        {
          step: "Capa 03 · Base Estructural",
          name: "Subcapa Blanca / Color de Alta Rigidez",
          desc: "Acabado interior limpio (disponible en bicapa Color/Blanco) que aporta luminosidad y resistencia al impacto sin mantenimiento.",
          color: "#4A4A45",
        },
      ],
    },
    wpc: {
      badge: "Interiorismo & Cielorrasos de Rápida Instalación",
      title: "Wall Panel WPC Acanalado & Cielo Razo PVC",
      subtitle:
        "Compuesto madera-polímero de última generación y paneles maderados/llanos que transforman paredes y tumbados en horas, sin obra húmeda.",
      saving: "0% absorción de humedad y polilla",
      lifespan: "Instalación 3x más rápida",
      norm: "Machihembrado invisible · Uso interior/cubierto",
      link: "/catalogo/?categoria=revestimientos-y-paneles",
      linkLabel: "Ver Wall Panel WPC y Cielorrasos",
      layers: [
        {
          step: "Capa 01 · Textura Arquitectónica",
          name: "Película Polimérica Veta Natural 3D",
          desc: "Tonos de alta demanda en Ecuador (Abedul Miel, Álamo Natural, Forest Nut, Negro/Gris) resistentes a rayaduras y limpieza frecuente.",
          color: "#C9A876",
        },
        {
          step: "Capa 02 · Cuerpo Estructural",
          name: "Núcleo Compuesto WPC / PVC Alveolar",
          desc: "Cámaras internas de aligeramiento que mejoran la acústica del salón u oficina e impiden deformaciones por humedad en Costa u Oriente.",
          color: "#6B4A2F",
        },
        {
          step: "Capa 03 · Fijación Técnica",
          name: "Pestaña de Anclaje Oculto con Clip",
          desc: "El tornillo queda 100% oculto tras el encaje de la siguiente pieza: acabado continuo de estudio de arquitectura.",
          color: "#161617",
        },
      ],
    },
    pisos: {
      badge: "Tráfico Comercial & Residencial Premium",
      title: "Pisos SPC Click & Porcelanato Gran Formato",
      subtitle:
        "Núcleo rígido de piedra caliza + polímero (SPC) y porcelanatos rectificados para remodelaciones limpias y obras nuevas de alto tránsito.",
      saving: "Instalación directa sin demoler piso previo",
      lifespan: "100% Hidrófugo (cocinas y locales)",
      norm: "Sistema Click Unilin · Capa de uso comercial",
      link: "/catalogo/?categoria=pisos",
      linkLabel: "Ver Pisos SPC y Porcelanatos",
      layers: [
        {
          step: "Capa 01 · Superficie de Desgaste",
          name: "Wear Layer UV + Textura Sincronizada",
          desc: "Protege contra abrasión de calzado comercial, sillas de oficina y manchas domésticas sin requerir encerado.",
          color: "#D4AF37",
        },
        {
          step: "Capa 02 · Estabilidad Dimensional",
          name: "Núcleo Rígido SPC (Stone Plastic Composite)",
          desc: "Alta densidad mineral que no se hincha con el agua ni se curva con los cambios térmicos entre el día y la noche.",
          color: "#3F3F46",
        },
        {
          step: "Capa 03 · Confort de Pisada",
          name: "Base Acústica IXPE + Encaje Click",
          desc: "Amortigua el sonido de pasos y permite nivelar sobre losa o baldosa existente en tiempo récord.",
          color: "#161617",
        },
      ],
    },
    policarbonato: {
      badge: "Iluminación Natural & Cubiertas Traslúcidas",
      title: "Policarbonato Alveolar & Accesorios de Sellado",
      subtitle:
        "Placas alveolares con coextrusión UV para pérgolas, tragaluces, invernaderos y cubiertas arquitectónicas con transmisión controlada de luz.",
      saving: "Hasta 80% ahorro en iluminación diurna",
      lifespan: "200x más resistente al impacto que el vidrio",
      norm: "Protección UV coextruida · Perfiles H y U",
      link: "/catalogo/?categoria=cielorrasos-y-techos",
      linkLabel: "Ver Policarbonato y Cielorrasos",
      layers: [
        {
          step: "Capa 01 · Escudo Solar",
          name: "Barrera Coextruida Anti-Amarilleamiento",
          desc: "Filtra la radiación ultravioleta dañina permitiendo el paso de luz natural difusa en tonos Cristal, Gris Perla, Bronce o Azul.",
          color: "#38BDF8",
        },
        {
          step: "Capa 02 · Cámara Térmica",
          name: "Estructura Celular Alveolar",
          desc: "Las celdas de aire internas reducen la transferencia térmica mientras mantienen un peso ultraligero para la estructura metálica.",
          color: "#64748B",
        },
        {
          step: "Capa 03 · Hermeticidad Total",
          name: "Perfiles de Policarbonato + Cinta y Tornillería",
          desc: "Complementado en nuestro catálogo con cumbreros, perfiles, cintas y tornillos autoperforantes con capuchón hermético.",
          color: "#D4AF37",
        },
      ],
    },
  };

  function initDidacticExplorer() {
    var tabs = document.querySelectorAll("[data-didactic-tab]");
    if (!tabs.length) return;

    var badgeEl = document.getElementById("didactic-badge");
    var titleEl = document.getElementById("didactic-title");
    var subtitleEl = document.getElementById("didactic-subtitle");
    var savingEl = document.getElementById("didactic-saving");
    var lifespanEl = document.getElementById("didactic-lifespan");
    var normEl = document.getElementById("didactic-norm");
    var linkEl = document.getElementById("didactic-link");
    var linkLabelEl = document.getElementById("didactic-link-label");
    var layersContainer = document.getElementById("didactic-layers");

    function renderMaterial(key) {
      var data = DIDACTIC_MATERIALS[key];
      if (!data) return;

      tabs.forEach(function (btn) {
        var active = btn.getAttribute("data-didactic-tab") === key;
        btn.setAttribute("aria-selected", active ? "true" : "false");
        if (active) {
          btn.classList.add("bg-secondary-container", "text-primary", "shadow-md");
          btn.classList.remove("bg-white/5", "text-on-primary");
        } else {
          btn.classList.remove("bg-secondary-container", "text-primary", "shadow-md");
          btn.classList.add("bg-white/5", "text-on-primary");
        }
      });

      if (badgeEl) badgeEl.textContent = data.badge;
      if (titleEl) titleEl.textContent = data.title;
      if (subtitleEl) subtitleEl.textContent = data.subtitle;
      if (savingEl) savingEl.textContent = data.saving;
      if (lifespanEl) lifespanEl.textContent = data.lifespan;
      if (normEl) normEl.textContent = data.norm;
      if (linkEl) linkEl.setAttribute("href", data.link);
      if (linkLabelEl) linkLabelEl.textContent = data.linkLabel;

      if (layersContainer) {
        var html = "";
        data.layers.forEach(function (layer, idx) {
          html +=
            '<div data-layer-card class="relative rounded-xl border border-white/10 bg-white/[0.04] p-4 transition-transform duration-300 hover:border-secondary-container/60" style="border-left: 4px solid ' +
            layer.color +
            '">' +
            '<div class="flex items-center justify-between gap-2">' +
            '<span class="font-label-sm text-xs uppercase tracking-widest text-secondary-fixed font-bold">' +
            layer.step +
            "</span>" +
            '<span class="inline-flex h-6 w-6 items-center justify-center rounded-full bg-white/10 text-xs font-bold text-on-primary">0' +
            (idx + 1) +
            "</span>" +
            "</div>" +
            '<h4 class="mt-1 font-headline-sm text-base font-bold text-on-primary">' +
            layer.name +
            "</h4>" +
            '<p class="mt-1 font-body-sm text-xs leading-relaxed text-surface-container-highest">' +
            layer.desc +
            "</p>" +
            "</div>";
        });
        layersContainer.innerHTML = html;

        if (typeof window.gsap !== "undefined" && !prefersReducedMotion) {
          window.gsap.fromTo(
            layersContainer.querySelectorAll("[data-layer-card]"),
            { y: 18, opacity: 0, rotateX: -8 },
            {
              y: 0,
              opacity: 1,
              rotateX: 0,
              duration: 0.45,
              stagger: 0.08,
              ease: "power2.out",
            }
          );
        }
      }

      if (window.MpiHero3D && typeof window.MpiHero3D.pulseProfile === "function") {
        window.MpiHero3D.pulseProfile(key);
      }
    }

    tabs.forEach(function (btn) {
      btn.addEventListener("click", function () {
        renderMaterial(btn.getAttribute("data-didactic-tab"));
      });
    });

    // Botón de expandir/contraer vista 3D de capas
    var explodeBtn = document.getElementById("didactic-explode-btn");
    var isExploded = false;
    if (explodeBtn && layersContainer) {
      explodeBtn.addEventListener("click", function () {
        isExploded = !isExploded;
        layersContainer.classList.toggle("gap-6", isExploded);
        layersContainer.classList.toggle("gap-3", !isExploded);
        explodeBtn.setAttribute("aria-pressed", isExploded ? "true" : "false");
        var cards = layersContainer.querySelectorAll("[data-layer-card]");
        if (typeof window.gsap !== "undefined" && !prefersReducedMotion) {
          cards.forEach(function (card, idx) {
            window.gsap.to(card, {
              x: isExploded ? idx * 10 : 0,
              scale: isExploded ? 1.02 : 1,
              duration: 0.35,
              ease: "power2.out",
            });
          });
        }
      });
    }
  }

  // ─────────────────────────────────────────────────────────────
  // 4. MICRO-INTERACCIÓN 3D EN TARJETAS (SOLO DESKTOP) & HTMX
  // ─────────────────────────────────────────────────────────────
  function bindCardInteractions(scope) {
    var root = scope || document;
    var isDesktop = window.innerWidth >= 1024 && !prefersReducedMotion;
    if (!isDesktop) return;

    var cards = root.querySelectorAll(".product-item, [data-tilt-card]");
    cards.forEach(function (card) {
      if (card.dataset.tiltBound === "1") return;
      card.dataset.tiltBound = "1";

      card.addEventListener(
        "mousemove",
        function (e) {
          var rect = card.getBoundingClientRect();
          var x = (e.clientX - rect.left) / Math.max(rect.width, 1) - 0.5;
          var y = (e.clientY - rect.top) / Math.max(rect.height, 1) - 0.5;
          card.style.transform =
            "perspective(900px) rotateX(" +
            (-y * 4).toFixed(2) +
            "deg) rotateY(" +
            (x * 4).toFixed(2) +
            "deg) translate3d(0, -3px, 0)";
        },
        { passive: true }
      );

      card.addEventListener(
        "mouseleave",
        function () {
          card.style.transform = "";
        },
        { passive: true }
      );
    });
  }

  function initHtmxHooks() {
    document.body.addEventListener("htmx:afterSwap", function (evt) {
      var target = evt.detail && evt.detail.target;
      if (!target) return;
      bindCardInteractions(target);

      if (typeof window.gsap !== "undefined" && !prefersReducedMotion) {
        var newCards = target.querySelectorAll(".product-item");
        if (newCards.length) {
          window.gsap.fromTo(
            newCards,
            { y: 20, opacity: 0 },
            {
              y: 0,
              opacity: 1,
              duration: 0.4,
              stagger: 0.04,
              ease: "power2.out",
            }
          );
        }
        if (typeof window.ScrollTrigger !== "undefined") {
          window.ScrollTrigger.refresh();
        }
      }
    });
  }

  // ─────────────────────────────────────────────────────────────
  // 5. BOOTSTRAP AL CARGAR EL DOM
  // ─────────────────────────────────────────────────────────────
  function boot() {
    initHero3D();
    initScrollAnimations();
    initDidacticExplorer();
    bindCardInteractions(document);
    initHtmxHooks();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
