(setq week-review ("R" "WEEK REVIEW"
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
)