(setq super-view-test ("t" "Super view test "
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
)