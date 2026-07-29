'use client';

import { Icon } from '@czi-sds/components';
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked';
import { Box, LinearProgress, Paper, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';

export type NavItem = { key: string; label: string; required: boolean };

export function SideNav({
  nav,
  active,
  done,
  subLabel,
  onJump,
}: {
  nav: NavItem[];
  active: string;
  done: Record<string, boolean>;
  subLabel: (key: string) => string;
  onJump: (key: string) => void;
}) {
  const requiredNav = nav.filter((n) => n.required);
  const doneReq = requiredNav.filter((n) => done[n.key]).length;
  const progress = requiredNav.length ? (doneReq / requiredNav.length) * 100 : 0;

  const statusIcon = (n: NavItem, isActive: boolean) => {
    if (!n.required) {
      return (
        <Box
          sx={{
            width: 20,
            height: 20,
            borderRadius: '50%',
            border: '2px dashed',
            borderColor: isActive ? 'primary.main' : 'text.disabled',
          }}
        />
      );
    }
    if (done[n.key]) return <Icon sdsIcon="CheckCircle" sdsSize="l" color="green" />;
    if (isActive) {
      return (
        <Box
          sx={{
            width: 20,
            height: 20,
            borderRadius: '50%',
            bgcolor: 'primary.main',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: 'common.white' }} />
        </Box>
      );
    }
    return <RadioButtonUncheckedIcon sx={{ fontSize: 22, color: 'grey.400' }} />;
  };

  return (
    <Box sx={{ width: 252, flexShrink: 0, position: 'sticky', top: 16, pr: 3, display: { xs: 'none', md: 'block' } }}>
      <Typography variant="overline" sx={{ color: 'text.secondary', fontWeight: 700, letterSpacing: 1.2 }}>
        On this page
      </Typography>
      <Box sx={{ mt: 1.5 }}>
        {nav.map((n, i) => {
          const isActive = active === n.key;
          const isLast = i === nav.length - 1;
          return (
            <Box key={n.key} sx={{ display: 'flex', gap: 1.25, alignItems: 'stretch' }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 22 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mt: '10px' }}>
                  {statusIcon(n, isActive)}
                </Box>
                {!isLast && <Box sx={{ width: 2, flex: 1, minHeight: 18, bgcolor: 'divider', mt: 0.5 }} />}
              </Box>
              <Box
                onClick={() => onJump(n.key)}
                sx={{
                  flex: 1,
                  mb: 1,
                  py: 1,
                  px: 1.5,
                  borderRadius: 1.5,
                  cursor: 'pointer',
                  bgcolor: 'transparent',
                  '&:hover': { bgcolor: 'action.hover' },
                }}
              >
                <Typography
                  variant="body2"
                  sx={{ fontWeight: isActive ? 700 : 600, color: 'text.primary', lineHeight: 1.3 }}
                >
                  {n.label}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25 }}>
                  {subLabel(n.key)}
                </Typography>
              </Box>
            </Box>
          );
        })}
      </Box>

      <Paper variant="outlined" sx={{ mt: 2, p: 2, borderRadius: 2, bgcolor: 'background.paper' }}>
        <Box sx={{ p: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="body2" sx={{ fontWeight: 700 }}>
            Required sections
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 700, color: 'primary.main' }}>
            {doneReq}/{requiredNav.length}
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={progress}
          sx={{
            borderRadius: 1,
            height: 6,
            mb: 4,
            bgcolor: (t) => alpha(t.palette.primary.main, 0.12),
            '& .MuiLinearProgress-bar': { borderRadius: 1 },
          }}
        />
      </Paper>
    </Box>
  );
}
