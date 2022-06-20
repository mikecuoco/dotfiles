;; -*- mode: emacs-lisp; lexical-binding: t -*-
;; This file is loaded by Spacemacs at startup.

(defun dotspacemacs/layers ()
  (load "~/.spacemacs.d/layers.el")
  )


(defun dotspacemacs/init ()
  (load "~/.spacemacs.d/options.el")
  )

(defun dotspacemacs/user-init ()
  "Initialization function for user code.
It is called immediately after `dotspacemacs/init', before layer configuration
executes.
 This function is mostly useful for variables that need to be set
before packages are loaded. If you are unsure, you should try in setting them in
`dotspacemacs/user-config' first."
  (setq ispell-program-name "/opt/homebrew/bin/aspell")
  )


(defun dotspacemacs/user-config ()
  (load "~/.spacemacs.d/user-config.el")
  (load "~/.spacemacs.d/agenda.el")
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
 '(package-selected-packages
   '(xah-fly-keys zonokai-emacs zenburn-theme zen-and-art-theme yasnippet-snippets xterm-color ws-butler writeroom-mode winum white-sand-theme which-key wgrep vterm volatile-highlights vimrc-mode vi-tilde-fringe uuidgen use-package undo-tree underwater-theme ujelly-theme twilight-theme twilight-bright-theme twilight-anti-bright-theme treemacs-projectile treemacs-persp treemacs-icons-dired treemacs-evil transpose-frame toxi-theme toc-org terminal-here tao-theme tangotango-theme tango-plus-theme tango-2-theme symon symbol-overlay sunny-day-theme sublime-themes subatomic256-theme subatomic-theme string-edit spaceline-all-the-icons spacegray-theme soothe-theme solarized-theme soft-stone-theme soft-morning-theme soft-charcoal-theme smyx-theme smex shell-pop seti-theme reverse-theme reveal-in-osx-finder restart-emacs request rebecca-theme rainbow-delimiters railscasts-theme quickrun purple-haze-theme professional-theme popwin planet-theme phoenix-dark-pink-theme phoenix-dark-mono-theme pcre2el password-generator paradox pandoc-mode ox-pandoc ox-hugo ox-gfm overseer osx-trash osx-dictionary osx-clipboard organic-green-theme org-wild-notifier org-superstar org-super-agenda org-roam-bibtex org-rich-yank org-ref org-projectile org-present org-pomodoro org-noter org-mime org-journal org-download org-contrib org-cliplink open-junk-file omtose-phellack-theme oldlace-theme occidental-theme obsidian-theme noctilux-theme naquadah-theme nameless mustang-theme multi-term multi-line monokai-theme monochrome-theme molokai-theme moe-theme modus-vivendi-theme modus-operandi-theme mmm-mode minimal-theme material-theme markdown-toc majapahit-theme madhat2r-theme macrostep lush-theme lorem-ipsum link-hint light-soap-theme launchctl kaolin-themes jbeans-theme jazz-theme ivy-yasnippet ivy-xref ivy-purpose ivy-hydra ivy-bibtex ivy-avy ir-black-theme inspector inkpot-theme info+ indent-guide hybrid-mode hungry-delete hl-todo highlight-parentheses highlight-numbers highlight-indentation heroku-theme hemisu-theme helm-make helm-dictionary hc-zenburn-theme gruvbox-theme gruber-darker-theme grandshell-theme gotham-theme google-translate golden-ratio gnuplot git-gutter-fringe gh-md gandalf-theme fuzzy font-lock+ flycheck-pos-tip flycheck-package flycheck-elsa flx-ido flatui-theme flatland-theme farmhouse-theme fancy-battery eziam-theme expand-region exotica-theme evil-visualstar evil-visual-mark-mode evil-unimpaired evil-tutor evil-textobj-line evil-surround evil-org evil-numbers evil-nerd-commenter evil-matchit evil-lisp-state evil-lion evil-indent-plus evil-iedit-state evil-goggles evil-exchange evil-escape evil-ediff evil-easymotion evil-collection evil-cleverparens evil-args evil-anzu eval-sexp-fu espresso-theme eshell-z eshell-prompt-extras esh-help emr elisp-slime-nav editorconfig dumb-jump drag-stuff dracula-theme dotenv-mode doom-themes django-theme dired-quick-sort diminish devdocs deft darktooth-theme darkokai-theme darkmine-theme darkburn-theme dakrone-theme dactyl-mode cyberpunk-theme counsel-projectile company-statistics company-reftex company-quickhelp company-math company-box company-auctex column-enforce-mode color-theme-sanityinc-tomorrow color-theme-sanityinc-solarized clues-theme clean-aindent-mode chocolate-theme cherry-blossom-theme centered-cursor-mode busybee-theme bubbleberry-theme browse-at-remote birds-of-paradise-plus-theme badwolf-theme auto-yasnippet auto-highlight-symbol auto-compile auctex-latexmk apropospriate-theme anti-zenburn-theme ample-zen-theme ample-theme alect-themes aggressive-indent afternoon-theme ace-link ac-ispell)))
(custom-set-faces
 ;; custom-set-faces was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 )
)
  "Emacs custom settings.
This is an auto-generated function, do not modify its content directly, use
Emacs customize menu instead.
This function is called at the very end of Spacemacs initialization."
