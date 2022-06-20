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

;; TODO: figure out to separate each view into a separate file
(setq org-agenda-custom-commands
    '(("r" agenda "Research"
        ((org-agenda-span 5)
        (org-agenda-files
        (append (directory-files-recursively "~/Dropbox/org/learn" "\\.org$")
                (directory-files-recursively "~/Dropbox/org/research" "\\.org$"))
        ))
    )
    ("R" "research"
         ((agenda "" (
                        (org-agenda-start-day "+0d")
                        (org-agenda-span 14)
                        (org-agenda-files
                         (append (directory-files-recursively "~/Dropbox/org/learn" "\\.org$")
                                 (directory-files-recursively "~/Dropbox/org/research" "\\.org$"))
                         )
                        (org-agenda-overriding-header "Scheduled")
                        (org-agenda-repeating-timestamp-show-all nil)
                        (org-agenda-remove-tags t)
                        ;;(org-agenda-prefix-format   "  %-3i  %-15b %t%s")
                        ;;(org-agenda-prefix-format " %-12:c %?-12t %b")
                        (org-agenda-prefix-format "%-4s ")
                        ))
            (alltodo "" (
                          (org-agenda-overriding-header "Unscheduled")
                          (org-agenda-files
                           (append (directory-files-recursively "~/Dropbox/org/learn" "\\.org$")
                                   (directory-files-recursively "~/Dropbox/org/research" "\\.org$"))
                           )
                          (org-agenda-remove-tags t)
                          ;; (org-agenda-prefix-format " %-3i %-15b %t%s")
                          ;; (org-agenda-prefix-format " %-12:c %?-12t %b")
                          (org-agenda-prefix-format " %b%?-12t ")
                          ;;(org-agenda-todo-keyword-format "")
                          (org-super-agenda-groups
                           '((:discard (:deadline past))
                             (:discard (:deadline today))
                             (:discard (:deadline future))
                             (:discard (:scheduled past))
                             (:discard (:scheduled today))
                             (:discard (:scheduled future))
                             (:name "Started"
                                    :todo "STARTED"
                                    :order 1)
                             (:name "Todo"
                                    :todo "TODO"
                                    :order 2)
                             (:name "Waiting"
                                    :todo "WAITING"
                                    :order 3)
                             (:name "On Hold"
                                    :todo "HOLD"
                                    :order 4))
                           )))
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

