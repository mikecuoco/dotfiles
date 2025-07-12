
  "Configuration function for user code.
This function is called at the very end of Spacemacs initialization after
layers configuration.
This is the place where most of your configurations should be done. Unless it is
explicitly specified that a variable should be set before a package is loaded,
you should place your code here."

  ;; startup settings
  ;; my keybindings
  (spacemacs/declare-prefix "an" "notes")
  (spacemacs/set-leader-keys
    "anh" 'helm-bibtex
    "ani" 'ivy-bibtex
    "ann" 'org-noter
    "ans" 'org-noter-create-skeleton)
  (spacemacs/set-leader-keys
    "w C-t" 'transpose-frame
    "awp" 'pocket-reader)
  ;; Drag stuff
;;   (define-key evil-normal-state-map (kbd "M-<up>") 'drag-stuff-up)
;;   (define-key evil-visual-state-map (kbd "M-<up>") 'drag-stuff-up)
;;   (define-key evil-normal-state-map (kbd "M-<down>") 'drag-stuff-down)
;;   (define-key evil-visual-state-map (kbd "M-<down>") 'drag-stuff-down)
  ;; (define-key evil-normal-state-map (kbd "C-M-<up>") 'org-move-subtree-up)
  ;; (define-key evil-normal-state-map (kbd "C-M-<down>") 'org-move-subtree-down)
  ;; Map moving to start of line to g h
  (define-key evil-normal-state-map (kbd "gh") 'evil-first-non-blank-of-visual-line)
  ;; Map moving to end of line to g l
  (define-key evil-normal-state-map (kbd "gl") 'evil-last-non-blank)
  ;; Map j to navigate down by a visual line (like g j)
  (define-key evil-normal-state-map (kbd "j") 'evil-next-visual-line)
  ;; Map k to navigate down by a visual line (like g k)
  (define-key evil-normal-state-map (kbd "k") 'evil-previous-visual-line)

;;'(global-git-commit-mode t) ;;
  (setq org-startup-indented t
        ;; show actually italicized text instead of /italicized text/
        org-hide-emphasis-markers t
        org-agenda-block-separator ""
        org-fontify-whole-heading-line t
        org-fontify-done-headline t
        org-fontify-quote-and-verse-blocks t
        org-return-follows-link t)
  (setq-default cursor-type 'bar) ;; cursor-type
  (spacemacs/toggle-truncate-lines-on) ;; wrap lines
  (view-echo-area-messages) ;; open echo on startup to check for errors/warnings
  (setq create-lockfiles nil) ;; Disable lock files
  (setq projectile-project-search-path '("~/Dropbox/org/")
        projectile-auto-discover nil)

   ;; ===== ALL THINGS ORG BELOW ===== ;;
  ;; set important paths to variables for easy reuse
  (with-eval-after-load 'org
    (org-defkey org-mode-map [(meta return)] 'org-meta-return)  ;; Fix for M-RET bug
    )

  (setq
   org_notes "~/Dropbox/org"
   org-mobile-inbox-for-pull "~/Dropbox/org/mobile.org"
   org-mobile-directory "~/Dropbox/Apps/MobileOrg"
   org-journal-dir "~/Dropbox/org/journal/"
   ;; org-journal-date-format "%A, %d %B %Y"
   zot_bib "~/Dropbox/zotero_library.bib"
   pdf_path "/Volumes/GoogleDrive/My Drive/zotero"
   )

  ;; org-mode refiling
  (setq org-refile-use-cache t
        org-refile-targets '((org-agenda-files :maxlevel . 4)
                             (nil :maxlevel . 5))
        org-refile-use-outline-path 'file ;; allows refiling into files as top header
        org-refile-allow-creating-parent-nodes t)

  ;; deft for quick file searching
  (setq
   deft-directory org_notes
   deft-extensions '("txt" "md" "org" "pdf")
   deft-recursive t
   )

   ;; org-roam setup
  (setq org-roam-directory org_notes
        org-directory org_notes
        org-roam-db-location (concat org_notes "org-roam.db")
        org-roam-v2-ack t)

  ;; (add-hook 'org-mode-hook 'org-roam-mode)

  (setq org-roam-capture-templates
        '(("d" "default" plain "%?"
           :if-new (file+head "${slug}.org"
                              "#+TITLE: ${title}\n#+AUTHOR: Mike Cuoco\n#+CREATED: %U
#+ROAM_ALIAS: ${roam_alias}\n#+ROAM_TAGS: %^G\n#+CATEGORY: ${category}\n- tags :: %^G")
           :unnarrowed t)
          ("t" "temp" plain "%?"
           :target (head "%<%Y%m%d%H%M%S>-${slug}"
                         "#+TITLE: ${title}\n")
           :unnarrowed t)))


  ;; reference management with org-roam-bibtex, helm-bibtex, org-ref, and org-noter
  ;; org-ref
  (setq
   org-ref-get-pdf-filename-function 'org-ref-get-pdf-filename-helm-bibtex
   org-ref-completion-library 'org-ref-ivy-cite
   org-ref-default-bibliography (list zot_bib)
;   org-ref-default-citation-link "cite"
   org-ref-bibliography-notes (concat org_notes "/bibnotes.org")
   org-ref-note-title-format "* TODO %y - %t\n :PROPERTIES:\n  :Custom_ID: %k\n  :NOTER_DOCUMENT: %F\n :ROAM_KEY: cite:%k\n  :AUTHOR: %9a\n  :JOURNAL: %j\n  :YEAR: %y\n  :VOLUME: %v\n  :PAGES: %p\n  :DOI: %D\n  :URL: %U\n :END:\n\n"
   org-ref-notes-directory org_notes
   org-ref-notes-function 'orb-edit-notes
   )

  ;; helm-/ivy-bibtex
  (setq
   bibtex-completion-notes-symbol "✎"
   bibtex-completion-notes-path org_notes
   bibtex-completion-bibliography zot_bib
   bibtex-completion-pdf-field nil
   bibtex-completion-notes-template-multiple-files
   (concat
    "#+TITLE: ${title}\n"
    "#+ROAM_KEY: cite:${=key=}\n"
    "* TODO Notes\n"
    ":PROPERTIES:\n"
    ":Custom_ID: ${=key=}\n"
    ":NOTER_DOCUMENT: %(orb-process-file-field \"${=key=}\")\n"
    ":AUTHOR: ${author-abbrev}\n"
    ":DATE: ${date}\n"
    ":YEAR: ${year}\n"
    ":DOI: ${doi}\n"
    ":URL: ${url}\n"
    ":END:\n\n"
    )
   )

  ;; org-roam-bibtex
  (add-hook 'org-roam-mode 'org-roam-bibtex-mode)
  (setq orb-preformat-keywords
        '("=key=" "title" "url" "file" "author-or-editor" "keywords"))
  (setq orb-templates
        '(("r" "ref" plain (function org-roam-capture--get-point)
           ""
           :file-name "literature/%<%Y-%m-%d-%H-%M-%S>-${slug}"
           :head "#+TITLE: ${=key=}: ${title}\n"
           "#+ROAM_KEY: ${ref}"
           "#+ROAM_TAGS: "
           "Time-stamp: <>"
           "- tags :: ${keywords}"
           "* ${title}
:PROPERTIES:
:Custom_ID: ${=key=}
:URL: ${url}
:AUTHOR: ${author-or-editor}
:NOTER_DOCUMENT: %(orb-process-file-field \"${=key=}\")
:NOTER_PAGE:
:END:
                                "
           :unnarrowed t)))

  (setq
   ;; The WM can handle splits
   ;;org-noter-notes-window-location 'other-frame
   ;; Please stop opening frames
   ;;org-noter-always-create-frame nil
   ;; I want to see the whole file
   org-noter-hide-other nil
   ;; Everything is relative to the rclone mega
   org-noter-notes-search-path org_notes
   )

  ;; open pdf with system pdf viewer (works on mac)
  (setq bibtex-completion-pdf-open-function
        (lambda (fpath)
          (start-process "open" "*open*" "open" fpath)))
;; org-mode task keywords:
(setq org-todo-keywords '((sequence "TODO(t)" "STARTED(s)" "|" "DONE(d)")
                        (sequence "TODO(t)" "NEXT(n)" "|" "DONE(d)")
                        (sequence "WAITING(w@/!)" "HOLD(h@/!)" "|" "CANCELLED(c@/!)" "PHONE" "MEETING")))

(setq org-todo-keyword-faces '(("TODO" :foreground "red" :weight bold)
                                ("STARTED" :foreground "royalblue" :weight bold)
                                ("NEXT" :foreground "pink" :weight bold)
                                ("DONE" :foreground "green" :weight bold)
                                ("WAITING" :foreground "orange" :weight bold)
                                ("HOLD" :foreground "magenta" :weight bold)
                                ("CANCELLED" :foreground "forest green" :weight bold)))

  ;; Changing a task state is done with C-c C-t KEY
  (setq org-use-fast-todo-selection t)
  (setq org-treat-S-cursor-todo-selection-as-state-change nil)

  ;; (setq org-agenda-hide-tags-regexp "HOLD\\|CANCELLED\\|DONE")
   
