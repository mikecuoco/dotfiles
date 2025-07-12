(setq my-week 
       "w" agenda "" 
              ((org-agenda-start-day "+0d")
              (org-agenda-span 7)
              (org-super-agenda-groups
                     '((:name ""
                            :todo "TODO"
                            :order 1)
                     (:name "Started"
                            :todo "STARTED"
                            :order 5)
                     (:name "Completed"
                            :todo "DONE"
                            :order 90)
                     (:name "On Hold"
                            :todo ("HOLD" "WAITING")
                            :order 95)

                     ))
              )
       
)