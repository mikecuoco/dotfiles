;; MY AGENDA CONFIGURATIONS ;;
;; org-mode super agenda
;; inspired by https://tinyurl.com/y5b2ewbt

(org-super-agenda-mode)
(setq org-agenda-files (directory-files-recursively "~/Dropbox/org" "\\.org$")
    org-super-agenda-header-map t
    org-agenda-prefix-format "  %-10:c%?-7t %-5s"
    org-agenda-scheduled-leaders '("" "%3dd" "%3dx")
    org-agenda-deadline-leaders '("" "%3dd" "%3dx")
    org-agenda-start-on-weekday nil
    org-agenda-dim-blocked-tasks nil
    org-deadline-warning-days 14
    org-scheduled-delay-days 0
    ;; org-super-agenda-keep-order t
    org-agenda-sorting-strategy '(habit-down priority-down deadline-up scheduled-up)
    org-agenda-use-tag-inheritance nil)

(defun load-directory (dir)
    (let ((load-it (lambda (f)
            (load-file (concat (file-name-as-directory dir) f)))
            ))
(mapc load-it (directory-files dir nil "\\.el$"))))
;; (load-directory "~/.spacemacs.d/agenda-views")
;; (load "~/.spacemacs.d/agenda-views/my-week.el")

(setq org-agenda-custom-commands
    '(("r" agenda "Research"
        ((org-agenda-span 5)
        (org-super-agenda-groups
            '(
            (:name ""
            :category "Research")
            (:discard (:anything t))
            )
        ))
    )
    ("h" agenda "Other"
        ((org-agenda-span 5)
        (org-super-agenda-groups
            '(
            (:name ""
            :not (:category "Research"))
            (:discard (:anything t))
            )
        ))
    ))
)

