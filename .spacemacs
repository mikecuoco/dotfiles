;; -*- mode: emacs-lisp; lexical-binding: t -*-
;; This file is loaded by Spacemacs at startup.
;; It must be stored in your home directory.

(defun dotspacemacs/layers ()
  "Configuration Layers declaration.
You should not put any user code in this function besides modifying the variable
values."

  (setq-default
   ;; Base distribution to use. This is a layer contained in the directory
   ;; `+distribution'. For now available distributions are `spacemacs-base'
   ;; or `spacemacs'. (default 'spacemacs)
   dotspacemacs-distribution 'spacemacs
   ;; Lazy installation of layers (i.e. layers are installed only when a file
   ;; with a supported type is opened). Possible values are `all', `unused'
   ;; and `nil'. `unused' will lazy install only unused layers (i.e. layers
   ;; not listed in variable `dotspacemacs-configuration-layers'), `all' will
   ;; lazy install any layer that support lazy installation even the layers
   ;; listed in `dotspacemacs-configuration-layers'. `nil' disable the lazy
   ;; installation feature and you have to explicitly list a layer in the
   ;; variable `dotspacemacs-configuration-layers' to install it.
   ;; (default 'unused)
   dotspacemacs-enable-lazy-installation 'unused
   ;; If non-nil then Spacemacs will ask for confirmation before installing
   ;; a layer lazily. (default t)
   dotspacemacs-ask-for-lazy-installation t
   ;; If non-nil layers with lazy install support are lazy installed.
   ;; List of additional paths where to look for configuration layers.
   ;; Paths must have a trailing slash (i.e. `~/.mycontribs/')
   dotspacemacs-configuration-layer-path '()
   ;; List of configuration layers to load.
   dotspacemacs-configuration-layers
   '(vimscript
     ;; ------------------------------
     ;; Example of useful layers you may want to use right away.
     ;; Uncomment some layer names and press <SPC f e R> (Vim style) or
     ;; <M-m f e R> (Emacs style) to install them.
     ;; ----------------------------------------------------------------
     osx
     pandoc
     helm
     ivy
     bibtex
     latex
     (auto-completion :variables
                      auto-completion-enable-snippets-in-popup t
                      auto-completion-enable-help-tooltip t
                      auto-completion-use-company-box t
                      auto-completion-enable-sort-by-usage t)
     ;; better-defaults
     emacs-lisp
     git
     markdown
     deft
     (calendar :variables
               org-gcal-client-id "1056185480745-ii2m227c28msriviuemilqg0jlnem47n.apps.googleusercontent.com"
               org-gcal-client-secret "xQ916mFYycskTJyJOtK2VbDZ"
               org-gcal-file-alist '(("mcuoco12@gmail.com" . "~/Dropbox/org/calendar/personal-schedule.org")
                                     ("mcuoco@ucsd.edu" . "~/Dropbox/org/calendar/ucsd-schedule.org")
                                     ("broadinstitute.com_74n3gg1q3o1g80hkgd7ighn904@group.calendar.google.com" . "~/Dropbox/org/calendar/seminars-schedule.org")
                                     ("c_egor2q4m86vlkod8memb60u22s@group.calendar.google.com" . "~/Dropbox/org/calendar/class-schedule.org")
                                     )
               )
     ;; org things
     (org :variables
          org-enable-org-journal-support t
          org-enable-hugo-support t
          org-enable-roam-support t
          )
     ;; shell and programming
     (shell :variables
             shell-default-height 30
             shell-default-positin 'bottom
             shell-default-shell 'vterm)
     shell-scripts
     (vimscript :variables vimscript-backend 'company-vimscript)
     ;; spell-checking
     ;;ess
     ;;python
     syntax-checking
     version-control
     ;; aesthetics
     themes-megapack
     theming
     )
   ;; List of additional packages that will be installed without being
   ;; wrapped in a layer. If you need some configuration for these
   ;; packages, then consider creating a layer. You can also put the
   ;; configuration in `dotspacemacs/user-config'.
   dotspacemacs-additional-packages
   '(
     drag-stuff
     doom-themes
     transpose-frame
     org-super-agenda
     helm-dictionary
     ;org-roam-bibtex
     ;org-noter
     )
   ;; A list of packages that cannot be updated.
   dotspacemacs-frozen-packages '()
   ;; A list of packages that will not be installed and loaded.
   dotspacemacs-excluded-packages '(
                                    evil-magit
                                    eyebrowse
                                    )
   ;; Defines the behaviour of Spacemacs when installing packages.
   ;; Possible values are `used-only', `used-but-keep-unused' and `all'.
   ;; `used-only' installs only explicitly used packages and uninstall any
   ;; unused packages as well as their unused dependencies.
   ;; `used-but-keep-unused' installs only the used packages but won't uninstall
   ;; them if they become unused. `all' installs *all* packages supported by
   ;; Spacemacs and never uninstall them. (default is `used-only')
   dotspacemacs-install-packages 'used-only))

(defun dotspacemacs/init ()
  "Initialization function.
This function is called at the very startup of Spacemacs initialization
before layers configuration.
You should not put any user code in there besides modifying the variable
values."
  ;; This setq-default sexp is an exhaustive list of all the supported
  ;; spacemacs settings.
  (setq-default
   ;; If non-nil then enable support for the portable dumper. You'll need
   ;; to compile Emacs 27 from source following the instructions in file
   ;; EXPERIMENTAL.org at to root of the git repository.
   ;; (default nil)
   dotspacemacs-enable-emacs-pdumper nil

   ;; Name of executable file pointing to emacs 27+. This executable must be
   ;; in your PATH.
   ;; (default "emacs")
   dotspacemacs-emacs-pdumper-executable-file "emacs"

   ;; Name of the Spacemacs dump file. This is the file will be created by the
   ;; portable dumper in the cache directory under dumps sub-directory.
   ;; To load it when starting Emacs add the parameter `--dump-file'
   ;; when invoking Emacs 27.1 executable on the command line, for instance:
   ;;   ./emacs --dump-file=$HOME/.emacs.d/.cache/dumps/spacemacs-27.1.pdmp
   ;; (default (format "spacemacs-%s.pdmp" emacs-version))
   dotspacemacs-emacs-dumper-dump-file (format "spacemacs-%s.pdmp" emacs-version)
   ;; If non nil ELPA repositories are contacted via HTTPS whenever it's
   ;; possible. Set it to nil if you have no way to use HTTPS in your
   ;; environment, otherwise it is strongly recommended to let it set to t.
   ;; This variable has no effect if Emacs is launched with the parameter
   ;; `--insecure' which forces the value of this variable to nil.
   ;; (default t)
   dotspacemacs-elpa-https t
   ;; Maximum allowed time in seconds to contact an ELPA repository.
   dotspacemacs-elpa-timeout 5
   ;; Set `gc-cons-threshold' and `gc-cons-percentage' when startup finishes.
   ;; This is an advanced option and should not be changed unless you suspect
   ;; performance issues due to garbage collection operations.
   ;; (default '(100000000 0.1))
   dotspacemacs-gc-cons '(100000000 0.1)

   ;; Set `read-process-output-max' when startup finishes.
   ;; This defines how much data is read from a foreign process.
   ;; Setting this >= 1 MB should increase performance for lsp servers
   ;; in emacs 27.
   ;; (default (* 1024 1024))
   dotspacemacs-read-process-output-max (* 4096 4096)

   ;; If non-nil then Spacelpa repository is the primary source to install
   ;; a locked version of packages. If nil then Spacemacs will install the
   ;; latest version of packages from MELPA. Spacelpa is currently in
   ;; experimental state please use only for testing purposes.
   ;; (default nil)
   dotspacemacs-use-spacelpa nil

   ;; If non-nil then verify the signature for downloaded Spacelpa archives.
   ;; (default t)
   dotspacemacs-verify-spacelpa-archives t
   ;; If non nil then spacemacs will check for updates at startup
   ;; when the current branch is not `develop'. Note that checking for
   ;; new versions works via git commands, thus it calls GitHub services
   ;; whenever you start Emacs. (default nil)
   dotspacemacs-check-for-update nil
   ;; If non-nil, a form that evaluates to a package directory. For example, to
   ;; use different package directories for different Emacs versions, set this
   ;; to `emacs-version'.
   dotspacemacs-elpa-subdirectory 'emacs-version
   ;; One of `vim', `emacs' or `hybrid'.
   ;; `hybrid' is like `vim' except that `insert state' is replaced by the
   ;; `hybrid state' with `emacs' key bindings. The value can also be a list
   ;; with `:variables' keyword (similar to layers). Check the editing styles
   ;; section of the documentation for details on available variables.
   ;; (default 'vim)
   dotspacemacs-editing-style 'vim
   ;; If non nil output loading progress in `*Messages*' buffer. (default nil)
   dotspacemacs-verbose-loading t
   ;; Specify the startup banner. Default value is `official', it displays
   ;; the official spacemacs logo. An integer value is the index of text
   ;; banner, `random' chooses a random text banner in `core/banners'
   ;; directory. A string value must be a path to an image format supported
   ;; by your Emacs build.
   ;; If the value is nil then no banner is displayed. (default 'official)
   dotspacemacs-startup-banner 'official
   ;; List of items to show in startup buffer or an association list of
   ;; the form `(list-type . list-size)`. If nil then it is disabled.
   ;; Possible values for list-type are:
   ;; `recents' `bookmarks' `projects' `agenda' `todos'."
   ;; List sizes may be nil, in which case
   ;; `spacemacs-buffer-startup-lists-length' takes effect.
   dotspacemacs-startup-lists '((recents . 5)
                                (agenda . 5)
                                (todos . 5))
   ;; True if the home buffer should respond to resize events.
   dotspacemacs-startup-buffer-responsive t
   ;; Default major mode of the scratch buffer (default `text-mode')
   dotspacemacs-scratch-mode 'text-mode
   ;; If non-nil, *scratch* buffer will be persistent. Things you write down in
   ;; *scratch* buffer will be saved and restored automatically.
   dotspacemacs-scratch-buffer-persistent nil

   ;; If non-nil, `kill-buffer' on *scratch* buffer
   ;; will bury it instead of killing.
   dotspacemacs-scratch-buffer-unkillable nil

   ;; Initial message in the scratch buffer, such as "Welcome to Spacemacs!"
   ;; (default nil)
   dotspacemacs-initial-scratch-message nil
   ;; List of themes, the first of the list is loaded when spacemacs starts.
   ;; Press <SPC> T n to cycle to the next theme in the list (works great
   ;; with 2 themes variants, one dark and one light)
   dotspacemacs-themes '(doom-spacegrey
                         spacemacs-dark
                         doom-oceanic-next
                         doom-snazzy
                         doom-one-light
                         tango-plus
                         spacemacs-light)
   ;; Set the theme for the Spaceline. Supported themes are `spacemacs',
   ;; `all-the-icons', `custom', `doom', `vim-powerline' and `vanilla'. The
   ;; first three are spaceline themes. `doom' is the doom-emacs mode-line.
   ;; `vanilla' is default Emacs mode-line. `custom' is a user defined themes,
   ;; refer to the DOCUMENTATION.org for more info on how to create your own
   ;; spaceline theme. Value can be a symbol or list with additional properties.
   ;; (default '(spacemacs :separator wave :separator-scale 1.5))
   ;; dotspacemacs-mode-line-theme '(spacemacs :separator wave :separator-scale 1.5)
   dotspacemacs-mode-line-theme '(doom)
   ;; If non nil the cursor color matches the state color in GUI Emacs.
   dotspacemacs-colorize-cursor-according-to-state t
   ;; Default font, or prioritized list of fonts. `powerline-scale' allows to
   ;; quickly tweak the mode-line size to make separators look not too crappy.
   ;;dotspacemacs-default-font '("Source Code Pro"
   dotspacemacs-default-font '("Source Code Pro"
                               :size 12
                               :weight normal
                               :width normal
                               :powerline-scale 1.0)
   ;; The leader key
   dotspacemacs-leader-key "SPC"
   ;; The key used for Emacs commands (M-x) (after pressing on the leader key).
   ;; (default "SPC")
   dotspacemacs-emacs-command-key "SPC"
   ;; The key used for Vim Ex commands (default ":")
   dotspacemacs-ex-command-key ":"
   ;; The leader key accessible in `emacs state' and `insert state'
   ;; (default "M-m")
   dotspacemacs-emacs-leader-key "M-m"
   ;; Major mode leader key is a shortcut key which is the equivalent of
   ;; pressing `<leader> m`. Set it to `nil` to disable it. (default ",")
   dotspacemacs-major-mode-leader-key ","
   ;; Major mode leader key accessible in `emacs state' and `insert state'.
   ;; (default "C-M-m")
   dotspacemacs-major-mode-emacs-leader-key "C-M-m"
   ;; These variables control whether separate commands are bound in the GUI to
   ;; the key pairs C-i, TAB and C-m, RET.
   ;; Setting it to a non-nil value, allows for separate commands under <C-i>
   ;; and TAB or <C-m> and RET.
   ;; In the terminal, these pairs are generally indistinguishable, so this only
   ;; works in the GUI. (default nil)
   dotspacemacs-distinguish-gui-tab nil
   ;; If non nil `Y' is remapped to `y$' in Evil states. (default nil)
   dotspacemacs-remap-Y-to-y$ nil
   ;; If non-nil, the shift mappings `<' and `>' retain visual state if used
   ;; there. (default t)
   dotspacemacs-retain-visual-state-on-shift t
   ;; If non-nil, J and K move lines up and down when in visual mode.
   ;; (default nil)
   dotspacemacs-visual-line-move-text nil
   ;; If non nil, inverse the meaning of `g' in `:substitute' Evil ex-command.
   ;; (default nil)
   dotspacemacs-ex-substitute-global nil
   ;; Name of the default layout (default "Default")
   dotspacemacs-default-layout-name "Default"
   ;; If non nil the default layout name is displayed in the mode-line.
   ;; (default nil)
   dotspacemacs-display-default-layout nil
   ;; If non nil then the last auto saved layouts are resume automatically upon
   ;; start. (default nil)
   dotspacemacs-auto-resume-layouts nil
   ;; Size (in MB) above which spacemacs will prompt to open the large file
   ;; literally to avoid performance issues. Opening a file literally means that
   ;; no major mode or minor modes are active. (default is 1)
   dotspacemacs-large-file-size 1
   ;; Location where to auto-save files. Possible values are `original' to
   ;; auto-save the file in-place, `cache' to auto-save the file to another
   ;; file stored in the cache directory and `nil' to disable auto-saving.
   ;; (default 'cache)
   dotspacemacs-auto-save-file-location 'original
   ;; Maximum number of rollback slots to keep in the cache. (default 5)
   dotspacemacs-max-rollback-slots 5
   ;; If non nil, `helm' will try to minimize the space it uses. (default nil)
   dotspacemacs-helm-resize nil
   ;; if non nil, the helm header is hidden when there is only one source.
   ;; (default nil)
   dotspacemacs-helm-no-header nil
   ;; define the position to display `helm', options are `bottom', `top',
   ;; `left', or `right'. (default 'bottom)
   dotspacemacs-helm-position 'bottom
   ;; Controls fuzzy matching in helm. If set to `always', force fuzzy matching
   ;; in all non-asynchronous sources. If set to `source', preserve individual
   ;; source settings. Else, disable fuzzy matching in all sources.
   ;; (default 'always)
   dotspacemacs-helm-use-fuzzy 'always
   ;; If non nil the paste micro-state is enabled. When enabled pressing `p`
   ;; several times cycle between the kill ring content. (default nil)
   dotspacemacs-enable-paste-transient-state nil
   ;; Which-key delay in seconds. The which-key buffer is the popup listing
   ;; the commands bound to the current keystroke sequence. (default 0.4)
   dotspacemacs-which-key-delay 0.2
   ;; Which-key frame position. Possible values are `right', `bottom' and
   ;; `right-then-bottom'. right-then-bottom tries to display the frame to the
   ;; right; if there is insufficient space it displays it at the bottom.
   ;; (default 'bottom)
   dotspacemacs-which-key-position 'bottom
   ;; If non nil a progress bar is displayed when spacemacs is loading. This
   ;; may increase the boot time on some systems and emacs builds, set it to
   ;; nil to boost the loading time. (default t)
   dotspacemacs-loading-progress-bar t
   ;; If non nil the frame is fullscreen when Emacs starts up. (default nil)
   ;; (Emacs 24.4+ only)
   dotspacemacs-fullscreen-at-startup t
   ;; If non nil `spacemacs/toggle-fullscreen' will not use native fullscreen.
   ;; Use to disable fullscreen animations in OSX. (default nil)
   dotspacemacs-fullscreen-use-non-native nil
   ;; If non nil the frame is maximized when Emacs starts up.
   ;; Takes effect only if `dotspacemacs-fullscreen-at-startup' is nil.
   ;; (default nil) (Emacs 24.4+ only)
   dotspacemacs-maximized-at-startup nil
   ;; A value from the range (0..100), in increasing opacity, which describes
   ;; the transparency level of a frame when it's active or selected.
   ;; Transparency can be toggled through `toggle-transparency'. (default 90)
   dotspacemacs-active-transparency 90
   ;; A value from the range (0..100), in increasing opacity, which describes
   ;; the transparency level of a frame when it's inactive or deselected.
   ;; Transparency can be toggled through `toggle-transparency'. (default 90)
   dotspacemacs-inactive-transparency 70
   ;; If non nil show the titles of transient states. (default t)
   dotspacemacs-show-transient-state-title t
   ;; If non nil show the color guide hint for transient state keys. (default t)
   dotspacemacs-show-transient-state-color-guide t
   ;; If non nil unicode symbols are displayed in the mode line. (default t)
   dotspacemacs-mode-line-unicode-symbols t
   dotspacemacs-mode-line-theme 'spacemacs
   ;; If non nil smooth scrolling (native-scrolling) is enabled. Smooth
   ;; scrolling overrides the default behavior of Emacs which recenters point
   ;; when it reaches the top or bottom of the screen. (default t)
   dotspacemacs-smooth-scrolling t
   ;; Control line numbers activation.
   ;; If set to `t' or `relative' line numbers are turned on in all `prog-mode' and
   ;; `text-mode' derivatives. If set to `relative', line numbers are relative.
   ;; This variable can also be set to a property list for finer control:
   ;; '(:relative nil
   ;;   :disabled-for-modes dired-mode
   ;;                       doc-view-mode
   ;;                       markdown-mode
   ;;                       org-mode
   ;;                       pdf-view-mode
   ;;                       text-mode
   ;;   :size-limit-kb 1000)
   ;; (default nil)
   dotspacemacs-line-numbers t
   ;; Code folding method. Possible values are `evil' and `origami'.
   ;; (default 'evil)
   dotspacemacs-folding-method 'evil
   ;; If non-nil smartparens-strict-mode will be enabled in programming modes.
   ;; (default nil)
   dotspacemacs-smartparens-strict-mode nil
   ;; If non-nil pressing the closing parenthesis `)' key in insert mode passes
   ;; over any automatically added closing parenthesis, bracket, quote, etc…
   ;; This can be temporary disabled by pressing `C-q' before `)'. (default nil)
   dotspacemacs-smart-closing-parenthesis nil
   ;; Select a scope to highlight delimiters. Possible values are `any',
   ;; `current', `all' or `nil'. Default is `all' (highlight any scope and
   ;; emphasis the current one). (default 'all)
   dotspacemacs-highlight-delimiters 'all
   ;; If non nil, advise quit functions to keep server open when quitting.
   ;; (default nil)
   dotspacemacs-persistent-server nil
   ;; List of search tool executable names. Spacemacs uses the first installed
   ;; tool of the list. Supported tools are `ag', `pt', `ack' and `grep'.
   ;; (default '("ag" "pt" "ack" "grep"))
   dotspacemacs-search-tools '("ag" "pt" "ack" "grep")
   ;; Format specification for setting the frame title.
   ;; %a - the `abbreviated-file-name', or `buffer-name'
   ;; %t - `projectile-project-name'
   ;; %I - `invocation-name'
   ;; %S - `system-name'
   ;; %U - contents of $USER
   ;; %b - buffer name
   ;; %f - visited file name
   ;; %F - frame name
   ;; %s - process status
   ;; %p - percent of buffer above top of window, or Top, Bot or All
   ;; %P - percent of buffer above bottom of window, perhaps plus Top, or Bot or All
   ;; %m - mode name
   ;; %n - Narrow if appropriate
   ;; %z - mnemonics of buffer, terminal, and keyboard coding systems
   ;; %Z - like %z, but including the end-of-line format
   ;; (default "%I@%S")
   dotspacemacs-frame-title-format "%I %a"


   ;; The default package repository used if no explicit repository has been
   ;; specified with an installed package.
   ;; Not used for now. (default nil)
   dotspacemacs-default-package-repository nil
   ;; Delete whitespace while saving buffer. Possible values are `all'
   ;; to aggressively delete empty line and long sequences of whitespace,
   ;; `trailing' to delete only the whitespace at end of lines, `changed'to
   ;; delete only whitespace for changed lines or `nil' to disable cleanup.
   ;; (default nil)
   dotspacemacs-whitespace-cleanup "trailing"
   ))

(defun dotspacemacs/user-init ()
  "Initialization function for user code.
It is called immediately after `dotspacemacs/init', before layer configuration
executes.
 This function is mostly useful for variables that need to be set
before packages are loaded. If you are unsure, you should try in setting them in
`dotspacemacs/user-config' first."
  (setq ispell-program-name "/usr/local/Cellar/aspell/0.60.8/bin/aspell")
  )

(defun dotspacemacs/user-config ()
  "Configuration function for user code.
This function is called at the very end of Spacemacs initialization after
layers configuration.
This is the place where most of your configurations should be done. Unless it is
explicitly specified that a variable should be set before a package is loaded,
you should place your code here."

  ;; startup settings
  ;;(global-git-commit-mode t) ;;magit
  (setq org-startup-indented t
        org-pretty-entities t
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
  ;; Drag lines up
  (define-key evil-normal-state-map (kbd "M-<up>") 'drag-stuff-up)
  (define-key evil-visual-state-map (kbd "M-<up>") 'drag-stuff-up)
  ;; Drag lines down
  (define-key evil-normal-state-map (kbd "M-<down>") 'drag-stuff-down)
  (define-key evil-visual-state-map (kbd "M-<down>") 'drag-stuff-down)
  ;; Map moving to start of line to g h
  (define-key evil-normal-state-map (kbd "gh") 'evil-first-non-blank-of-visual-line)
  ;; Map moving to end of line to g l
  (define-key evil-normal-state-map (kbd "gl") 'evil-last-non-blank)
  ;; Map j to navigate down by a visual line (like g j)
  (define-key evil-normal-state-map (kbd "j") 'evil-next-visual-line)
  ;; Map k to navigate down by a visual line (like g k)
  (define-key evil-normal-state-map (kbd "k") 'evil-previous-visual-line)

  ;; ===== ALL THINGS ORG BELOW ===== ;;
  ;; set important paths to variables for easy reuse
  (setq
   org_notes "~/Dropbox/org"
   org-mobile-inbox-for-pull "~/Dropbox/org/flagged.org"
   org-mobile-directory "~/Dropbox/Apps/MobileOrg"
   zot_bib "~/Dropbox/zotero_library.bib"
   pdf_path "/Volumes/GoogleDrive/My Drive/zotero"
   )

  ;; deft for quick file searching
  (setq
   deft-directory org_notes
   deft-extensions '("txt" "md" "org" "pdf")
   ;deft-recursive t
   )

  ;; org-mode refiling
  (setq org-refile-use-cache t
        org-refile-targets '((org-agenda-files :maxlevel . 3)
                             (nil :maxlevel . 5))
        org-refile-use-outline-path t
        org-refile-allow-creating-parent-nodes t)

  ;; org-roam setup
  (setq
   org-roam-directory org_notes
   org-directory org_notes
   org-roam-db-location (concat org_notes "org-roam.db")
   )
  (add-hook 'org-mode-hook 'org-roam-mode)

  (setq org-roam-capture-templates
        '(("d" "default" plain #'org-roam--capture-get-point "%?"
           :file-name "${slug}"
           :head "#+TITLE: ${title}\n#+AUTHOR: Mike Cuoco\n#+CREATED: %U
#+ROAM_ALIAS: ${roam_alias}\n#+ROAM_TAGS: %^G\n#+CATEGORY: ${category}\n- tags :: %^G"
           :unnarrowed t)
          ("t" "temp" plain #'org-roam--capture-get-point "%?"
           :file-name "%<%Y%m%d%H%M%S>-${slug}"
           :head "#+TITLE: ${title}\n"
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

  (setq org-todo-keyword-faces '(("TODO" . (org-warning :weight bold))
                                 ("STARTED" . "#dc752f")
                                 ("WAITING" . "orange")
                                 ("CANCELLED" . "#f2241f")))


  (setq org-todo-keyword-faces '(("TODO" :foreground "red" :weight bold)
                                 ("STARTED" :foreground "royalblue" :weight bold)
                                 ("NEXT" :foreground "pink" :weight bold)
                                 ("DONE" :foreground "green" :weight bold)
                                 ("WAITING" :foreground "orange" :weight bold)
                                 ("HOLD" :foreground "magenta" :weight bold)
                                 ("CANCELLED" :foreground "forest green" :weight bold)
                                 ("MEETING" :foreground "forest green" :weight bold)
                                 ("PHONE" :foreground "forest green" :weight bold)))

  ;; Changing a task state is done with C-c C-t KEY
  (setq org-use-fast-todo-selection t)
  (setq org-treat-S-cursor-todo-selection-as-state-change nil)

  ;; org-mode super agenda
  ;; inspired by https://tinyurl.com/y5b2ewbt

  (org-super-agenda-mode)
  (setq org-agenda-files (list "~/Dropbox/org" "~/Dropbox/org/calendar")
        org-super-agenda-header-map nil
        org-deadline-warning-days 10
        org-scheduled-delay-days 0
        org-agenda-skip-scheduled-delay-if-deadline t
        org-agenda-start-on-weekday nil
        org-agenda-dim-blocked-tasks nil)

  (setq org-agenda-hide-tags-regexp "HOLD\\|CANCELLED\\|DONE")

  (setq org-agenda-custom-commands
        '(("t" "Test Schedule"
           ((agenda "" ((org-agenda-overriding-header "Schedule")
                        (org-agenda-compact-blocks t)
                        (org-agenda-span 'day)
                        (org-agenda-ndays 1)
	                      (org-agenda-start-on-weekday nil)
                        (org-agenda-scheduled-leaders '("" " %2dx:"))
                        (org-agenda-deadline-leaders '("" " %2dd:" "%2dd ago: "))
	                      (org-agenda-start-day "+0d")
                        (org-agenda-prefix-format " %-5s %?-12t %b ")
                        (org-super-agenda-groups
                         '((:name "Schedule"
                                  :time-grid t
                                  :log t)
                           (:name "Habits"
                                  :habit t
                                  :order 5)
                           (:name "Important"
                                  :priority>= "A"
                                  :order 8)
                           (:name "Inbox"
                                  :category "Inbox"
                                  :log t
                                  :order 10)
                           (:name "Rotation"
                                  :category "Rotation"
                                  :log t
                                  :order 20)
                           (:name "Class"
                                  :category "Class"
                                  :log t
                                  :order 30)
                           (:name "Reading"
                                  :tag ":reading:"
                                  :log t
                                  :order 25)
                           (:name "UCSD"
                                  :category "UCSD"
                                  :log t
                                  :order 30)
                           (:auto-category t
                                           :log t
                                           :order 99)
                           ))
                        ))))
          ("z" "Super view"
           ((agenda "" ((org-agenda-span 'day)
                        (org-agenda-prefix-format " %-5s %?-12t ")
                        (org-agenda-block-separator nil)
                        (org-agenda-compact-blocks t)
                        (org-super-agenda-groups
                         '((:name "Schedule"
                           :time-grid t
                           :order 1)
                           (:discard (:anything t))))))
            (agenda "" ((org-agenda-overriding-header "")
                        (org-agenda-format-date "")
                        (org-agenda-span 'day)
                        (org-agenda-block-separator nil)
                        (org-agenda-compact-blocks t)
                        (org-agenda-prefix-format "  %-12:c%?-12t % s %b")
                        (org-agenda-skip-deadline-if-done t)
                        (org-agenda-log-mode t)
                        (org-agenda-scheduled-leaders '("" " %2dx"))
                        (org-agenda-deadline-leaders '("" " %2dd" "%2dd ago"))
                        (org-super-agenda-groups
                         '((:log t)
                           (:name "Habits"
                                  :habit t
                                  :order 1)
                           (:name "Overdue"
                                  :deadline past
                                  :order 2)
                           (:name "Due Today"
                                  :deadline today
                                  :order 3)
                           (:name "Today"
                                  :scheduled today
                                  :order 5)
                           (:name "Past"
                                  :scheduled past
                                  :order 4)
                           (:name "Due Soon"
                                  :deadline future
                                  :order 20)
                           (:discard (:anything t))))))
            (alltodo "" ((org-agenda-overriding-header "")
                         (org-agenda-prefix-format " %?-12t %b ")
                         (org-agenda-block-separator nil)
                         (org-agenda-compact-blocks t)
                         (org-super-agenda-groups
                          '((:discard (:habit t))
                            (:discard (:deadline past))
                            (:discard (:deadline today))
                            (:discard (:deadline future))
                            (:discard (:scheduled today))
                            (:discard (:scheduled tomorrow))
                            (:discard (:todo "HOLD"))
                            (:name "Started"
                                   :todo "STARTED"
                                   :order 1)
                            (:name "Important"
                                   :priority>= "B"
                                   :order 2)
                            (:name "Waiting"
                                   :todo "WAITING"
                                   :order 5)
                            (:name "Research"
                                   :category "Research"
                                   :log t
                                   :order 20)
                            (:name "Class"
                                   :category "Class"
                                   :log t
                                   :order 30)
                            (:name "Fellowships"
                                   :category "Fellowships"
                                   :order 50)
                            (:name "Outreach"
                                   :category "Outreach"
                                   :order 60)
                            (:auto-category t
                                            :log t
                                            :order 99)
                            ))))))
          ("o" "My Agenda"
           ((todo "TODO" (
                          (org-agenda-overriding-header "\n⚡ Do Today\n┄┄┄┄┄┄┄┄┄┄")
                          (org-agenda-remove-tags t)
                          ;;(org-agenda-prefix-format " %-3i %-15b %t%s")
                          (org-agenda-prefix-format " %-i %-12:c %?-12t")
                          ;;(org-agenda-todo-keyword-format "")
                          ))
            (agenda "" (
                        (org-agenda-start-day "+0d")
                        (org-agenda-span 5)
                        (org-agenda-overriding-header "⚡ Schedule\n┄┄┄┄┄┄┄┄┄┄")
                        (org-agenda-repeating-timestamp-show-all nil)
                        (org-agenda-remove-tags t)
                        ;;(org-agenda-prefix-format   "  %-3i  %-15b %t%s")
                        (org-agenda-prefix-format " %-i %-12:c %?-12t")
                        ;;(org-agenda-todo-keyword-format " ☐ ")
                        (org-agenda-scheduled-leaders '("" ""))
                        ))))
          ("r" "WEEK REVIEW"
           ((todo "DONE"
                  (
                   (Org-agenda-overriding-header "DONE!")
                   ))
            (todo "CANCELLED"
                  ((org-agenda-overriding-header "CANCELLED")))
            (todo "TODO"
                  ((org-agenda-overriding-header "TODO Items (without time attached)")
                   (org-agenda-skip-function '(org-agenda-skip-entry-if 'deadline 'scheduled 'timestamp))))
            (todo "WAIT"
                  ((org-agenda-overriding-header "WAIT: Items on hold (without time attached)")
                   (org-agenda-skip-function '(org-agenda-skip-entry-if 'deadline 'scheduled 'timestamp))))
            )
           )
          ))

  ;; org-gcal
  ;;(add-hook 'org-agenda-mode-hook 'org-gcal-fetch)
  ;;(run-with-timer 0 (* 30 60) 'org-gcal-fetch) ;; fetch calendar evennts every 30 minutes
)

;; Do not write anything past this comment. This is where Emacs will
;; auto-generate custom variable definitions.
(custom-set-faces
 ;; custom-set-faces was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 )
(defun dotspacemacs/emacs-custom-settings ()
  "Emacs custom settings.
This is an auto-generated function, do not modify its content directly, use
Emacs customize menu instead.
This function is called at the very end of Spacemacs initialization."
(custom-set-variables
 ;; custom-set-variables was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 '(ansi-color-names-vector
   ["#d2ceda" "#f2241f" "#67b11d" "#b1951d" "#3a81c3" "#a31db1" "#21b8c7" "#655370"])
 '(cursor-type 'bar)
 '(evil-want-Y-yank-to-eol nil)
 '(fci-rule-color "#383a42")
 '(hl-todo-keyword-faces
   '(("TODO" . "#dc752f")
     ("NEXT" . "#dc752f")
     ("THEM" . "#2d9574")
     ("PROG" . "#3a81c3")
     ("OKAY" . "#3a81c3")
     ("DONT" . "#f2241f")
     ("FAIL" . "#f2241f")
     ("DONE" . "#42ae2c")
     ("NOTE" . "#b1951d")
     ("KLUDGE" . "#b1951d")
     ("HACK" . "#b1951d")
     ("TEMP" . "#b1951d")
     ("FIXME" . "#dc752f")
     ("XXX+" . "#dc752f")
     ("\\?\\?\\?+" . "#dc752f")))
 '(jdee-db-active-breakpoint-face-colors (cons "#f0f0f0" "#4078f2"))
 '(jdee-db-requested-breakpoint-face-colors (cons "#f0f0f0" "#50a14f"))
 '(jdee-db-spec-breakpoint-face-colors (cons "#f0f0f0" "#9ca0a4"))
 '(objed-cursor-color "#e45649")
 '(org-super-agenda-date-format "%A %e %B")
 '(package-selected-packages
   '(vimrc-mode helm-gtags ggtags dactyl-mode counsel-gtags insert-shebang flycheck-bashate fish-mode company-shell drag-stuff auctex-latexmk wgrep smex ivy-yasnippet ivy-xref ivy-purpose ivy-hydra ivy-bibtex ivy-avy counsel-projectile counsel swiper xterm-color unfill smeargle shell-pop orgit org-roam emacsql-sqlite3 emacsql org-projectile org-category-capture org-present org-pomodoro alert log4e gntp org-mime org-download mwim multi-term mmm-mode markdown-toc markdown-mode magit-gitflow magit-popup htmlize helm-gitignore helm-company helm-c-yasnippet gnuplot gitignore-mode gitconfig-mode gitattributes-mode git-timemachine git-messenger git-link git-gutter-fringe+ git-gutter-fringe fringe-helper git-gutter+ git-gutter gh-md fuzzy flyspell-correct-helm flyspell-correct flycheck-pos-tip pos-tip flycheck evil-magit magit git-commit with-editor transient eshell-z eshell-prompt-extras esh-help diff-hl company-statistics company auto-yasnippet yasnippet auto-dictionary ac-ispell auto-complete ws-butler winum which-key volatile-highlights vi-tilde-fringe uuidgen use-package toc-org spaceline powerline restart-emacs request rainbow-delimiters popwin persp-mode pcre2el paradox spinner org-plus-contrib org-bullets open-junk-file neotree move-text macrostep lorem-ipsum linum-relative link-hint indent-guide hydra lv hungry-delete hl-todo highlight-parentheses highlight-numbers parent-mode highlight-indentation helm-themes helm-swoop helm-projectile projectile pkg-info epl helm-mode-manager helm-make helm-flx helm-descbinds helm-ag google-translate golden-ratio flx-ido flx fill-column-indicator fancy-battery eyebrowse expand-region exec-path-from-shell evil-visualstar evil-visual-mark-mode evil-unimpaired f evil-tutor evil-surround evil-search-highlight-persist highlight evil-numbers evil-nerd-commenter evil-mc evil-matchit evil-lisp-state smartparens evil-indent-plus evil-iedit-state iedit evil-exchange evil-escape evil-ediff evil-args evil-anzu anzu evil goto-chg undo-tree eval-sexp-fu elisp-slime-nav dumb-jump dash s diminish define-word column-enforce-mode clean-aindent-mode bind-map bind-key auto-highlight-symbol auto-compile packed aggressive-indent adaptive-wrap ace-window ace-link ace-jump-helm-line helm avy helm-core popup async))
 '(pdf-view-midnight-colors (cons "#383a42" "#fafafa"))
 '(rustic-ansi-faces
   ["#fafafa" "#e45649" "#50a14f" "#986801" "#4078f2" "#a626a4" "#0184bc" "#383a42"])
 '(vc-annotate-background "#fafafa")
 '(vc-annotate-color-map
   (list
    (cons 20 "#50a14f")
    (cons 40 "#688e35")
    (cons 60 "#807b1b")
    (cons 80 "#986801")
    (cons 100 "#ae7118")
    (cons 120 "#c37b30")
    (cons 140 "#da8548")
    (cons 160 "#c86566")
    (cons 180 "#b74585")
    (cons 200 "#a626a4")
    (cons 220 "#ba3685")
    (cons 240 "#cf4667")
    (cons 260 "#e45649")
    (cons 280 "#d2685f")
    (cons 300 "#c07b76")
    (cons 320 "#ae8d8d")
    (cons 340 "#383a42")
    (cons 360 "#383a42")))
 '(vc-annotate-very-old-color nil))
(custom-set-faces
 ;; custom-set-faces was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 )
)

