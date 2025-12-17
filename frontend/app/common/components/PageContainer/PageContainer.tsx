import { Box, Container, BoxProps, ContainerProps } from '@mui/material';
import { ReactNode } from 'react';

interface PageContainerProps {
  children: ReactNode;
  maxWidth?: ContainerProps['maxWidth'];
  py?: BoxProps['py'];
}

/**
 * PageContainer - Standardized page layout wrapper
 *
 * Provides consistent page styling with:
 * - Full viewport height minimum
 * - Configurable vertical padding (default: 3)
 * - Configurable max width container (default: 'lg')
 *
 * @example
 * ```tsx
 * <PageContainer maxWidth="md" py={4}>
 *   <Paper>Your content here</Paper>
 * </PageContainer>
 * ```
 */
export const PageContainer = ({ children, maxWidth = 'lg', py = 3 }: PageContainerProps) => {
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#ffffff', py }}>
      <Container maxWidth={maxWidth}>{children}</Container>
    </Box>
  );
};
