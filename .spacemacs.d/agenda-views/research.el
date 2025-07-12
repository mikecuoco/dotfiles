(setq research ("r" "Research"
           ;; TODO add habits at top
           ;; Rendering is quite slow
           ((agenda "" (
                        (org-agenda-start-day "+0d")
                        (org-agenda-span 14)
                        (org-agenda-files
                         (append (directory-files-recursively "~/Dropbox/org/learn" "\\.org$")
                                 (directory-files-recursively "~/Dropbox/org/research" "\\.org$"))
                         )
                        (org-agenda-overriding-header "⚡ Schedule\n┄┄┄┄┄┄┄┄┄┄")
                        (org-agenda-repeating-timestamp-show-all nil)
                        (org-agenda-remove-tags t)
                        ;;(org-agenda-prefix-format   "  %-3i  %-15b %t%s")
                        ;;(org-agenda-prefix-format " %-12:c %?-12t %b")
                        (org-agenda-prefix-format "%-4s ")
                        ))
            (alltodo "" (
                          (org-agenda-overriding-header "\n⚡ Unscheduled\n┄┄┄┄┄┄┄┄┄┄")
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
                             (:name "Waiting"
                                    :todo "WAITING"
                                    :order 2)
                             (:name "On Hold"
                                    :todo "HOLD"
                                    :order 3))
                           )))
            ))
)