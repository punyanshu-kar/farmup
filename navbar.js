/* =========================================================================
   FarmUp Universal Navigation JS (Drawer, Megamenu & Auth-Awareness)
   ========================================================================= */
(function() {
  function initNav() {
    const hamburger = document.getElementById('hamburger');
    const drawer = document.getElementById('mobileDrawer');
    const backdrop = document.getElementById('mobileBackdrop');
    const closeBtn = document.getElementById('drawerCloseBtn');
    const accordionBtn = document.getElementById('mobDistressAccordionBtn');
    const accordion = document.getElementById('mobDistressAccordion');
    const authBtn = document.getElementById('navAuthBtn');

    // Update Auth buttons if FarmUpAuth is loaded
    if (typeof FarmUpAuth !== 'undefined' && FarmUpAuth.isLoggedIn && FarmUpAuth.isLoggedIn()) {
      const prof = FarmUpAuth.getProfile ? FarmUpAuth.getProfile() : null;
      const displayName = (prof && prof.name) ? prof.name.split(' ')[0] : 'Farmer';
      if (authBtn) {
        authBtn.textContent = '👤 ' + displayName;
        authBtn.href = 'profile.html';
        authBtn.style.background = '#123B1E';
      }
    }

    function openDrawer() {
      if (drawer) drawer.classList.add('open');
      if (backdrop) backdrop.classList.add('open');
      document.body.style.overflow = 'hidden';
    }

    function closeDrawer() {
      if (drawer) drawer.classList.remove('open');
      if (backdrop) backdrop.classList.remove('open');
      document.body.style.overflow = '';
    }

    if (hamburger) {
      hamburger.addEventListener('click', (e) => {
        e.stopPropagation();
        openDrawer();
      });
    }

    if (closeBtn) {
      closeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        closeDrawer();
      });
    }

    if (backdrop) {
      backdrop.addEventListener('click', closeDrawer);
    }

    if (accordionBtn && accordion) {
      accordionBtn.addEventListener('click', (e) => {
        e.preventDefault();
        accordion.classList.toggle('open');
      });
    }

    // Assistant triggers
    document.querySelectorAll('.tb-ask-trigger').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        if (window.FarmUpSarvamAI && window.FarmUpSarvamAI.openAssistant) {
          window.FarmUpSarvamAI.openAssistant();
        } else {
          window.location.href = 'disease.html';
        }
      });
    });

    // Close mobile drawer on resize to desktop
    window.addEventListener('resize', () => {
      if (window.innerWidth >= 1024) {
        closeDrawer();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNav);
  } else {
    initNav();
  }
})();
